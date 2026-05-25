export function SummaryCard({ items }: { items: string[] }) {
  return <section className="card"><h2>Summary</h2>{items.length === 0 ? <p>Chưa có tóm tắt.</p> : <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>}</section>;
}
