interface MessageBubbleProps {
  type: 'user' | 'assistant';
  content: string;
}

export function MessageBubble({ type, content }: MessageBubbleProps) {
  const isUser = type === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[75%] px-5 py-3.5 rounded-2xl ${
          isUser
            ? 'bg-[#c89968] text-white rounded-br-md'
            : 'bg-[#f9f7f4] border border-[#e4dad0] text-[#5a3d2b] rounded-bl-md'
        }`}
      >
        <p>{content}</p>
      </div>
    </div>
  );
}
