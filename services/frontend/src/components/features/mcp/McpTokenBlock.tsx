import { Bot, Check, Copy, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { apiClient } from "../../../lib/clients/api";
import { Button } from "../../ui/Button";

export function McpTokenBlock() {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showToken, setShowToken] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchToken = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient<{ mcp_token: string }>(
        "/api/v1/users/mcp-token",
      );
      setToken(data.mcp_token);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch MCP token";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (!token) return;
    navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-foreground text-base">
                MCP AI Admin Interface
              </h3>
              <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/20">
                <ShieldCheck className="h-3 w-3" /> Superuser Only
              </span>
            </div>
            <p className="text-xs text-muted mt-1">
              Connect AI clients (Claude Desktop, Cursor, MCP Inspector) to
              inspect users, manage subscriptions, and debug scrapers.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-error/15 text-error text-sm font-medium border border-error/30">
          {error}
        </div>
      )}

      {!token ? (
        <Button
          variant="secondary"
          size="sm"
          isLoading={isLoading}
          onClick={fetchToken}
          leftIcon={<Bot className="h-4 w-4 text-primary" />}
        >
          Reveal MCP Bearer Token
        </Button>
      ) : (
        <div className="space-y-3 pt-2 border-t border-border">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted">
              Static MCP API Key (Bearer Token)
            </label>
            <div className="flex items-center gap-2">
              <div className="flex-1 relative font-mono text-sm px-3.5 py-2.5 rounded-lg bg-background border border-border text-foreground flex items-center justify-between overflow-hidden">
                <span className="truncate select-all">
                  {showToken ? token : "•".repeat(32)}
                </span>
                <button
                  type="button"
                  onClick={() => setShowToken(!showToken)}
                  className="text-muted hover:text-foreground transition-colors ml-2"
                  title={showToken ? "Hide token" : "Show token"}
                >
                  {showToken ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>

              <Button
                variant="secondary"
                size="md"
                onClick={handleCopy}
                leftIcon={
                  copied ? (
                    <Check className="h-4 w-4 text-success" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )
                }
              >
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-background/50 border border-border/60 text-xs space-y-1 text-muted">
            <p className="font-semibold text-foreground">
              Claude Desktop Config:
            </p>
            <p className="font-mono text-[11px] text-muted">
              Server URL:{" "}
              <span className="text-foreground">http://localhost:8000/mcp</span>
            </p>
            <p className="font-mono text-[11px] text-muted">
              Authorization:{" "}
              <span className="text-foreground">Bearer {token}</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
