import { CheckCircle2, ExternalLink, RefreshCw, Send } from "lucide-react";
import { useState } from "react";
import { useTelegramLink } from "../../../hooks/useTelegramLink";
import { Button } from "../../ui/Button";

export function TelegramConnectBlock() {
  const {
    telegramChatId,
    telegramUrl,
    isGeneratingLink,
    generateLink,
    pollStatus,
  } = useTelegramLink();
  const [isPolling, setIsPolling] = useState(false);

  const handlePoll = async () => {
    setIsPolling(true);
    try {
      await pollStatus();
    } finally {
      setIsPolling(false);
    }
  };

  if (telegramChatId) {
    return (
      <div className="rounded-xl border border-success/30 bg-success/10 p-5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="h-6 w-6 text-success" />
          <div>
            <h4 className="font-semibold text-foreground text-sm">
              Telegram Connected
            </h4>
            <p className="text-xs text-muted">
              Chat ID: <span className="font-mono">{telegramChatId}</span>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-5 space-y-4">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-primary/10 text-primary">
          <Send className="h-5 w-5" />
        </div>
        <div>
          <h4 className="font-semibold text-foreground text-sm">
            Telegram Instant Notifications
          </h4>
          <p className="text-xs text-muted mt-0.5">
            Connect our Telegram bot to get instant notifications when prices
            drop.
          </p>
        </div>
      </div>

      {!telegramUrl ? (
        <Button
          variant="primary"
          size="sm"
          isLoading={isGeneratingLink}
          onClick={() => generateLink()}
          leftIcon={<Send className="h-4 w-4" />}
        >
          Connect Telegram Bot
        </Button>
      ) : (
        <div className="space-y-3 pt-2 border-t border-border">
          <a
            href={telegramUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            <span>Open Bot in Telegram</span>
            <ExternalLink className="h-4 w-4" />
          </a>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              isLoading={isPolling}
              onClick={handlePoll}
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            >
              Я підключив (Check Status)
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
