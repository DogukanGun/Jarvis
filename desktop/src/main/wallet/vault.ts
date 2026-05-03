import { app } from 'electron'
import { Keypair } from '@solana/web3.js'
import { mnemonicToSeedSync, generateMnemonic, validateMnemonic } from 'bip39'
import { derivePath } from 'ed25519-hd-key'
import bs58Module from 'bs58'

// bs58 v6 ships as ESM; under Electron's CJS interop it lands as
// `{ default: { encode, decode } }` instead of `{ encode, decode }`.
// Resolve once defensively so both shapes work.
const bs58 = ((bs58Module as unknown as { default?: typeof bs58Module }).default ??
  bs58Module) as { encode: (b: Uint8Array) => string; decode: (s: string) => Uint8Array }
import { join } from 'path'
import { existsSync, readFileSync, writeFileSync, unlinkSync } from 'fs'
import {
  randomBytes,
  scryptSync,
  createCipheriv,
  createDecipheriv,
  timingSafeEqual,
} from 'crypto'

// File layout (binary, single-blob):
//   [salt: 16][iv: 12][authTag: 16][ciphertext: secretKey 64]
// Total: 108 bytes for SOL keypair.
//
// We also write a sidecar `wallet.pub.json` containing only { publicKey }, so the
// renderer can show the address without unlocking. Public key is not sensitive.

const SOL_DERIVATION_PATH = "m/44'/501'/0'/0'"

const SALT_LEN = 16
const IV_LEN = 12
const TAG_LEN = 16
const SCRYPT_N = 2 ** 15
const SCRYPT_R = 8
const SCRYPT_P = 1
const SCRYPT_KEYLEN = 32
// scrypt memory cost is ~128 * N * r bytes; with N=2^15, r=8 that's 32 MiB —
// exactly at OpenSSL's default cap, which it rejects. Bump the ceiling so the
// derivation actually fits.
const SCRYPT_MAXMEM = 64 * 1024 * 1024

function vaultPath(): string {
  return join(app.getPath('userData'), 'wallet.enc')
}

function pubPath(): string {
  return join(app.getPath('userData'), 'wallet.pub.json')
}

export function hasVault(): boolean {
  return existsSync(vaultPath())
}

export function getStoredPublicKey(): string | null {
  try {
    if (!existsSync(pubPath())) return null
    const raw = readFileSync(pubPath(), 'utf-8')
    const data = JSON.parse(raw) as { publicKey?: string }
    return data.publicKey ?? null
  } catch {
    return null
  }
}

function deriveKey(pin: string, salt: Buffer): Buffer {
  return scryptSync(pin, salt, SCRYPT_KEYLEN, {
    N: SCRYPT_N,
    r: SCRYPT_R,
    p: SCRYPT_P,
    maxmem: SCRYPT_MAXMEM,
  })
}

function keypairFromMnemonic(mnemonic: string): Keypair {
  if (!validateMnemonic(mnemonic.trim())) {
    throw new Error('Invalid mnemonic')
  }
  const seed = mnemonicToSeedSync(mnemonic.trim()).toString('hex')
  const { key } = derivePath(SOL_DERIVATION_PATH, seed)
  return Keypair.fromSeed(key)
}

function keypairFromBase58(base58: string): Keypair {
  const decoded = bs58.decode(base58.trim())
  if (decoded.length !== 64) {
    throw new Error('Invalid base58 secret key length')
  }
  return Keypair.fromSecretKey(decoded)
}

function encryptSecretKey(secretKey: Uint8Array, pin: string): Buffer {
  const salt = randomBytes(SALT_LEN)
  const iv = randomBytes(IV_LEN)
  const key = deriveKey(pin, salt)
  const cipher = createCipheriv('aes-256-gcm', key, iv)
  const ct = Buffer.concat([cipher.update(Buffer.from(secretKey)), cipher.final()])
  const tag = cipher.getAuthTag()
  return Buffer.concat([salt, iv, tag, ct])
}

function decryptSecretKey(blob: Buffer, pin: string): Uint8Array {
  if (blob.length < SALT_LEN + IV_LEN + TAG_LEN + 32) {
    throw new Error('Vault file is corrupt or truncated')
  }
  const salt = blob.subarray(0, SALT_LEN)
  const iv = blob.subarray(SALT_LEN, SALT_LEN + IV_LEN)
  const tag = blob.subarray(SALT_LEN + IV_LEN, SALT_LEN + IV_LEN + TAG_LEN)
  const ct = blob.subarray(SALT_LEN + IV_LEN + TAG_LEN)
  const key = deriveKey(pin, salt)
  const decipher = createDecipheriv('aes-256-gcm', key, iv)
  decipher.setAuthTag(tag)
  return new Uint8Array(Buffer.concat([decipher.update(ct), decipher.final()]))
}

function writeVault(secretKey: Uint8Array, pin: string, publicKey: string): void {
  const blob = encryptSecretKey(secretKey, pin)
  writeFileSync(vaultPath(), blob, { mode: 0o600 })
  writeFileSync(pubPath(), JSON.stringify({ publicKey }, null, 2), { mode: 0o600 })
}

export type CreateMode =
  | { kind: 'generate' }
  | { kind: 'mnemonic'; mnemonic: string }
  | { kind: 'base58'; base58: string }

export interface CreateResult {
  publicKey: string
  mnemonic: string | null
}

export function createVault(mode: CreateMode, pin: string): CreateResult {
  if (hasVault()) throw new Error('Vault already exists')
  if (!pin || pin.length < 4) throw new Error('PIN must be at least 4 characters')

  let kp: Keypair
  let mnemonic: string | null = null

  if (mode.kind === 'generate') {
    mnemonic = generateMnemonic(128)
    kp = keypairFromMnemonic(mnemonic)
  } else if (mode.kind === 'mnemonic') {
    kp = keypairFromMnemonic(mode.mnemonic)
  } else {
    kp = keypairFromBase58(mode.base58)
  }

  const publicKey = kp.publicKey.toBase58()
  writeVault(kp.secretKey, pin, publicKey)
  return { publicKey, mnemonic }
}

export function unlockVault(pin: string): Keypair {
  if (!hasVault()) throw new Error('No vault')
  const blob = readFileSync(vaultPath())
  const secretKey = decryptSecretKey(blob, pin)
  return Keypair.fromSecretKey(secretKey)
}

export function wipeVault(): void {
  try { if (existsSync(vaultPath())) unlinkSync(vaultPath()) } catch { /* ignore */ }
  try { if (existsSync(pubPath())) unlinkSync(pubPath()) } catch { /* ignore */ }
}

// Used for "verify PIN" without unlocking — checks decryption succeeds.
export function verifyPin(pin: string): boolean {
  try {
    const kp = unlockVault(pin)
    // wipe local reference; GC will clear
    void kp.publicKey
    return true
  } catch {
    return false
  }
}

// Decrypts the vault with the given PIN and returns the secret key in both
// formats commonly needed by Solana wallets:
//   base58: 88-char string (Solana CLI / Solflare / Backpack)
//   array : 64-element Uint8Array (Phantom "Import Wallet" expects this)
// Caller must have already biometric-gated this; PIN is required as a
// second factor so an unlocked-but-unattended app can't leak the key.
export function exportSecretKey(pin: string): { base58: string; array: number[] } {
  const kp = unlockVault(pin)
  return {
    base58: bs58.encode(kp.secretKey),
    array: Array.from(kp.secretKey),
  }
}

// Constant-time string compare for the loopback shared secret (Phase 2).
export function safeCompare(a: string, b: string): boolean {
  const bufA = Buffer.from(a)
  const bufB = Buffer.from(b)
  if (bufA.length !== bufB.length) return false
  return timingSafeEqual(bufA, bufB)
}
