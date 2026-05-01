export interface TraderConfig {
  port: number
  loopbackPort: number
  loopbackToken: string
  rpcUrl: string
  publicKey: string
  network: 'mainnet' | 'devnet'
}

function required(name: string): string {
  const v = process.env[name]
  if (!v) {
    console.error(`[solana-trader] missing required env: ${name}`)
    process.exit(1)
  }
  return v
}

export function loadConfig(): TraderConfig {
  const port = Number(process.env.PORT ?? 8901)
  const loopbackPort = Number(required('LOOPBACK_PORT'))
  const loopbackToken = required('LOOPBACK_TOKEN')
  const rpcUrl = required('RPC_URL')
  const publicKey = required('WALLET_PUBKEY')
  const network = (process.env.NETWORK === 'mainnet' ? 'mainnet' : 'devnet') as 'mainnet' | 'devnet'
  return { port, loopbackPort, loopbackToken, rpcUrl, publicKey, network }
}
