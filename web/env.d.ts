/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Public A2A endpoint of the agent; never a secret.
  readonly VITE_AGENT_URL: string
}
