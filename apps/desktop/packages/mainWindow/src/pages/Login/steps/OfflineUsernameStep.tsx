import { Show, createMemo, createSignal } from "solid-js"
import { Trans } from "@gd/i18n"
import { Button } from "@gd/ui"
import { useFlow } from "../flow/FlowContext"

/**
 * OfflineUsernameStep
 *
 * Offline account creation step.
 * Validates username format (3-16 chars, alphanumeric + underscore)
 * and creates a local offline profile with a stable UUID.
 */
export function OfflineUsernameStep() {
  const flow = useFlow()
  const [username, setUsername] = createSignal("")
  const [loading, setLoading] = createSignal(false)
  const [error, setError] = createSignal<string | null>(null)

  const isValid = createMemo(() => {
    const name = username()
    if (name.length < 3 || name.length > 16) return false
    return /^[a-zA-Z0-9_]+$/.test(name)
  })

  const handleCreate = async () => {
    if (!isValid()) return
    setLoading(true)
    setError(null)
    try {
      await flow.createOfflineAccount(username())
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create offline account")
      setLoading(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && isValid() && !loading()) {
      handleCreate()
    }
  }

  return (
    <div class="flex w-full flex-1 flex-col items-center justify-center gap-8 p-6 text-center">
      <div class="flex flex-col items-center justify-center gap-6">
        {/* Icon */}
        <div class="bg-darkSlate-600 flex h-20 w-20 items-center justify-center rounded-2xl">
          <div class="i-hugeicons:user-circle h-12 w-12 text-lightSlate-50" />
        </div>

        {/* Title */}
        <h2 class="text-lightSlate-50 m-0 text-xl font-semibold">
          <Trans key="auth:_trn_offline.title" />
        </h2>

        {/* Description */}
        <p class="text-lightSlate-400 m-0 max-w-md text-base leading-relaxed">
          <Trans key="auth:_trn_offline.description" />
        </p>

        <div class="w-full max-w-md">
          <input
            type="text"
            value={username()}
            onInput={(e) => setUsername(e.currentTarget.value)}
            onKeyDown={handleKeyDown}
            placeholder="Username"
            class="border-darkSlate-600 bg-darkSlate-700 text-lightSlate-50 placeholder:text-lightSlate-700 w-full rounded-lg border px-4 py-3 focus:border-primary-500 focus:outline-none"
            maxLength={16}
            disabled={loading()}
          />

          {/* Validation feedback */}
          <div class="mt-2 min-h-6 text-left text-sm">
            <Show when={username().length > 0 && !isValid()}>
              <p class="text-red-400">
                <Trans key="auth:_trn_offline.invalid_format" />
              </p>
            </Show>
          </div>

          {/* Requirements */}
          <div class="text-lightSlate-600 mt-4 text-left text-xs">
            <ul class="list-disc space-y-1 pl-5">
              <li
                classList={{
                  "text-green-400":
                    username().length >= 3 && username().length <= 16
                }}
              >
                <Trans key="auth:_trn_offline.requirement_length" />
              </li>
              <li
                classList={{
                  "text-green-400":
                    username().length > 0 &&
                    /^[a-zA-Z0-9_]*$/.test(username())
                }}
              >
                <Trans key="auth:_trn_offline.requirement_characters" />
              </li>
            </ul>
          </div>
        </div>

        <Show when={error()}>
          <p class="text-red-400 text-sm">{error()}</p>
        </Show>

        {/* Create button */}
        <Button
          size="large"
          variant="primary"
          fullWidth
          onClick={handleCreate}
          loading={loading()}
          disabled={!isValid() || loading()}
        >
          <Trans key="auth:_trn_offline.create_button" />
        </Button>

        {/* Warning */}
        <p class="text-lightSlate-600 m-0 max-w-md text-xs leading-relaxed">
          <Trans key="auth:_trn_offline.warning" />
        </p>
      </div>
    </div>
  )
}
