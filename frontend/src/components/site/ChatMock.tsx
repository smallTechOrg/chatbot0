export interface MockMessage {
  from: "visitor" | "agent";
  text: string;
}

/** A decorative chat mock-up for the hero of a page. */
export default function ChatMock({ url, messages, lead }: { url: string; messages: MockMessage[]; lead: string }) {
  return (
    <div className="pub-mock" aria-hidden="true">
      <div className="pub-mock__bar">
        <span className="pub-mock__dots">
          <i />
          <i />
          <i />
        </span>
        <span className="pub-mock__url">{url}</span>
      </div>
      <div className="pub-mock__body">
        {messages.map((m) => (
          <p key={m.text} className={`pub-bubble pub-bubble--${m.from}`}>
            {m.text}
          </p>
        ))}
        <p className="pub-mock__lead">
          <span className="pub-dot" />
          {lead}
        </p>
      </div>
      <div className="pub-mock__input">Type a message…</div>
    </div>
  );
}
