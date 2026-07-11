import { LatexBlock } from "./LatexBlock";

export function ProofTree(): JSX.Element {
  return (
    <div className="space-y-2">
      <ProofNode title="Why did the state change?" body="Because the simulator multiplies the state vector by the full unitary operator." />
      <ProofNode title="Why that full operator?" body="Because a gate on one wire is embedded with tensor products of identities on the untouched wires." />
      <ProofNode title="Why tensor products?" body="Because a multi-qubit basis is a product basis: |q0 q1 ...> = |q0> otimes |q1> otimes ..." />
      <LatexBlock math={"(A\\otimes B)_{(i,k),(j,l)}=A_{ij}B_{kl}"} compact />
      <ProofNode title="Why probabilities?" body="Because the Born rule maps each complex amplitude to a real observable probability with |a|^2." />
    </div>
  );
}

function ProofNode({ title, body }: { title: string; body: string }): JSX.Element {
  return (
    <div className="math-proof-node">
      <p className="font-mono text-[11px] text-text-primary">{title}</p>
      <p className="text-xs leading-5 text-text-secondary">{body}</p>
    </div>
  );
}
