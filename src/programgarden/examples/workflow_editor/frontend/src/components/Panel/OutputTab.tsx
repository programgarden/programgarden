interface OutputTabProps {
  output: unknown;
}

export default function OutputTab({ output }: OutputTabProps) {
  if (!output) {
    return (
      <div className="text-gray-500 text-center py-8">
        <p className="text-lg mb-2">📭 No output yet</p>
        <p className="text-xs">Run the workflow to see this node's output.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-400">
        ✅ Last execution output
      </p>

      <pre className="text-xs text-green-400 bg-gray-700/50 p-3 rounded-lg overflow-auto max-h-96">
        {JSON.stringify(output, null, 2)}
      </pre>
    </div>
  );
}
