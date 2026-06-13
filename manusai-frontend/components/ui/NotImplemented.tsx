import { Construction } from "lucide-react";

interface Props {
  title: string;
  description?: string;
}

export default function NotImplemented({ title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <div className="w-16 h-16 bg-gray-800 rounded-2xl flex items-center justify-center mb-4">
        <Construction className="w-8 h-8 text-yellow-400" />
      </div>
      <h2 className="text-white text-xl font-semibold mb-2">{title}</h2>
      <p className="text-gray-500 text-sm max-w-sm">
        {description || "Not Implemented Yet — This feature will be available in a future phase."}
      </p>
      <div className="mt-6 px-4 py-2 bg-yellow-900/30 border border-yellow-700/40 rounded-lg text-yellow-400 text-xs font-medium">
        Coming in Phase 1+
      </div>
    </div>
  );
}
