
interface Props {
  onStartPipeline: (idea: string) => void;
}

export const Intake: React.FC<Props> = ({ onStartPipeline }) => {
  const [idea, setIdea] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!idea.trim()) return;
    onStartPipeline(idea);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 pt-8">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold font-heading text-white">BrandCrucible Engine</h1>
        <p className="text-[var(--color-muted)] text-sm">
          Enter a raw startup idea to trigger the 7-stage adversarial multi-agent brand engine.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6 rounded-xl space-y-4">
        <div>
          <label className="block text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-2">
            Startup Idea
          </label>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g., An AI app that helps college students find hackathon teammates based on skills and availability..."
            rows={4}
            className="w-full bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg p-3 text-sm text-white placeholder-[var(--color-muted)] focus:outline-none focus:border-[var(--color-accent)] resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={!idea.trim()}
          className="w-full bg-[var(--color-accent)] hover:opacity-90 disabled:opacity-40 text-[#0B1020] font-bold py-3 rounded-lg text-sm transition-all cursor-pointer"
        >
          Fire Up Brand Engine →
        </button>
      </form>
    </div>
  );
};