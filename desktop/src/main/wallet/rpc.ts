import {
  Connection,
  PublicKey,
  LAMPORTS_PER_SOL,
  SystemProgram,
  Transaction,
  Keypair,
  sendAndConfirmTransaction,
} from '@solana/web3.js'
import {
  TOKEN_PROGRAM_ID,
  TOKEN_2022_PROGRAM_ID,
  getAssociatedTokenAddress,
  createAssociatedTokenAccountInstruction,
  createTransferCheckedInstruction,
  getMint,
} from '@solana/spl-token'
import { loadConfig } from './config'

function connection(): Connection {
  return new Connection(loadConfig().rpcUrl, 'confirmed')
}

export interface SolBalance {
  lamports: number
  sol: number
}

export async function getSolBalance(pubkey: string): Promise<SolBalance> {
  const conn = connection()
  const lamports = await conn.getBalance(new PublicKey(pubkey))
  return { lamports, sol: lamports / LAMPORTS_PER_SOL }
}

export interface TokenHolding {
  mint: string
  amount: string         // raw amount as string (BigInt-safe)
  uiAmount: number
  decimals: number
  tokenAccount: string
  programId: string
}

export async function getTokenHoldings(pubkey: string): Promise<TokenHolding[]> {
  const conn = connection()
  const owner = new PublicKey(pubkey)

  const out: TokenHolding[] = []
  for (const programId of [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]) {
    const resp = await conn.getParsedTokenAccountsByOwner(owner, { programId })
    for (const { pubkey: ata, account } of resp.value) {
      // @ts-ignore parsed shape
      const info = account.data.parsed?.info
      if (!info) continue
      const amount: string = info.tokenAmount?.amount ?? '0'
      const decimals: number = info.tokenAmount?.decimals ?? 0
      const uiAmount: number = info.tokenAmount?.uiAmount ?? 0
      if (uiAmount === 0) continue
      out.push({
        mint: info.mint,
        amount,
        uiAmount,
        decimals,
        tokenAccount: ata.toBase58(),
        programId: programId.toBase58(),
      })
    }
  }
  return out
}

export async function sendSol(
  signer: Keypair,
  to: string,
  sol: number,
): Promise<string> {
  const conn = connection()
  const lamports = Math.floor(sol * LAMPORTS_PER_SOL)
  if (lamports <= 0) throw new Error('Amount must be > 0')

  const tx = new Transaction().add(
    SystemProgram.transfer({
      fromPubkey: signer.publicKey,
      toPubkey: new PublicKey(to),
      lamports,
    }),
  )

  return sendAndConfirmTransaction(conn, tx, [signer], { commitment: 'confirmed' })
}

export async function sendSpl(
  signer: Keypair,
  to: string,
  mint: string,
  uiAmount: number,
): Promise<string> {
  const conn = connection()
  const mintPub = new PublicKey(mint)
  const toPub = new PublicKey(to)

  const mintInfo = await getMint(conn, mintPub).catch(async () =>
    getMint(conn, mintPub, undefined, TOKEN_2022_PROGRAM_ID),
  )

  // Detect which token program owns the mint by re-reading the account.
  const acctInfo = await conn.getAccountInfo(mintPub)
  if (!acctInfo) throw new Error('Mint account not found')
  const programId = acctInfo.owner

  const fromAta = await getAssociatedTokenAddress(mintPub, signer.publicKey, false, programId)
  const toAta = await getAssociatedTokenAddress(mintPub, toPub, false, programId)

  const tx = new Transaction()

  // Create destination ATA if missing.
  const toAtaInfo = await conn.getAccountInfo(toAta)
  if (!toAtaInfo) {
    tx.add(
      createAssociatedTokenAccountInstruction(
        signer.publicKey,
        toAta,
        toPub,
        mintPub,
        programId,
      ),
    )
  }

  const raw = BigInt(Math.floor(uiAmount * 10 ** mintInfo.decimals))
  tx.add(
    createTransferCheckedInstruction(
      fromAta,
      mintPub,
      toAta,
      signer.publicKey,
      raw,
      mintInfo.decimals,
      [],
      programId,
    ),
  )

  return sendAndConfirmTransaction(conn, tx, [signer], { commitment: 'confirmed' })
}

// `api.devnet.solana.com` is effectively the only public RPC that exposes
// `requestAirdrop` without an API key — and it's heavily rate-limited.
// PublicNode returns 404 for requestAirdrop; Ankr started requiring keys.
// On failure we surface a "Open web faucet" button (faucet.solana.com),
// which is the only reliable path when the public RPC is throttled.
const DEVNET_AIRDROP_FALLBACKS = [
  'https://api.devnet.solana.com',
]

async function tryAirdropOnce(rpcUrl: string, pubkey: PublicKey, lamports: number): Promise<string> {
  const conn = new Connection(rpcUrl, 'confirmed')
  // Two retries with backoff on the same endpoint — the public faucet
  // sometimes returns "Internal error" once and then succeeds.
  let lastErr: Error | null = null
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const sig = await conn.requestAirdrop(pubkey, lamports)
      const latest = await conn.getLatestBlockhash('confirmed')
      await conn.confirmTransaction(
        { signature: sig, blockhash: latest.blockhash, lastValidBlockHeight: latest.lastValidBlockHeight },
        'confirmed',
      )
      return sig
    } catch (e) {
      lastErr = e as Error
      if (attempt === 0) await new Promise((r) => setTimeout(r, 1500))
    }
  }
  throw lastErr ?? new Error('airdrop failed')
}

export async function airdropDevnetSol(pubkey: string, sol: number): Promise<string> {
  if (loadConfig().network !== 'devnet') throw new Error('Airdrop only available on devnet')
  const lamports = Math.floor(sol * LAMPORTS_PER_SOL)
  const target = new PublicKey(pubkey)

  const cfgUrl = loadConfig().rpcUrl
  const candidates = Array.from(new Set([cfgUrl, ...DEVNET_AIRDROP_FALLBACKS]))

  const errors: string[] = []
  for (const url of candidates) {
    try {
      return await tryAirdropOnce(url, target, lamports)
    } catch (err) {
      const msg = (err as Error).message || String(err)
      errors.push(`${new URL(url).host}: ${msg}`)
    }
  }

  // Public RPC is rate-limited. The renderer renders an "Open web faucet"
  // button when it sees the structured `code` below.
  const err = new Error(
    `Public devnet faucet is rate-limited. Use the web faucet at https://faucet.solana.com instead. Tried: ${errors.join(' | ')}`,
  ) as Error & { code?: string; webFaucetUrl?: string }
  err.code = 'DEVNET_FAUCET_RATE_LIMIT'
  err.webFaucetUrl = `https://faucet.solana.com/?walletAddress=${pubkey}&amount=${sol}`
  throw err
}
