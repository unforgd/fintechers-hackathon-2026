// Anchor the custody-log root of a claim on Solana devnet with one Memo transaction.
// Usage: node anchor/anchor.mjs VAX-001
// The devnet keypair lives outside the repo (~/.config/unforgd-devnet.json) and holds only free test SOL.
import { Connection, Keypair, LAMPORTS_PER_SOL, PublicKey, Transaction, TransactionInstruction,
         sendAndConfirmTransaction, clusterApiUrl } from "@solana/web3.js";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const MEMO = new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr");
const claimId = process.argv[2] || "VAX-001";
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const assessment = JSON.parse(fs.readFileSync(path.join(root, "results", `${claimId}.assessment.json`)));
const logRoot = assessment.chain.root;
const decision = `${assessment.liable_role || "none"}|EUR${assessment.recoverable_eur}`;

const keyFile = path.join(os.homedir(), ".config", "unforgd-devnet.json");
let payer;
if (fs.existsSync(keyFile)) payer = Keypair.fromSecretKey(Uint8Array.from(JSON.parse(fs.readFileSync(keyFile))));
else {
  payer = Keypair.generate();
  fs.mkdirSync(path.dirname(keyFile), { recursive: true });
  fs.writeFileSync(keyFile, JSON.stringify(Array.from(payer.secretKey)), { mode: 0o600 });
}
const conn = new Connection(clusterApiUrl("devnet"), "confirmed");
console.log("devnet payer", payer.publicKey.toBase58());
if ((await conn.getBalance(payer.publicKey)) < 0.01 * LAMPORTS_PER_SOL) {
  console.log("requesting devnet airdrop…");
  const sig = await conn.requestAirdrop(payer.publicKey, 0.5 * LAMPORTS_PER_SOL);
  await conn.confirmTransaction(sig, "confirmed");
}
const memo = `unforgd:${claimId}:custody-root:${logRoot}:decision:${decision}`;
const tx = new Transaction().add(new TransactionInstruction({ keys: [], programId: MEMO, data: Buffer.from(memo) }));
const signature = await sendAndConfirmTransaction(conn, tx, [payer]);
const out = { claim_id: claimId, root: logRoot, memo, signature, cluster: "devnet",
              explorer: `https://explorer.solana.com/tx/${signature}?cluster=devnet`, anchored_at: new Date().toISOString() };
fs.writeFileSync(path.join(root, "results", `${claimId}.anchor.json`), JSON.stringify(out, null, 1));
console.log(out.explorer);
