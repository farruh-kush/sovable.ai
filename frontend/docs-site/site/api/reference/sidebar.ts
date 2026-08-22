import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebar: SidebarsConfig = {
  apisidebar: [
    {
      type: "doc",
      id: "api/reference/ai-routing-layer-api-gateway",
    },
    {
      type: "category",
      label: "Health",
      collapsed: false,
      items: [
        {
          type: "doc",
          id: "api/reference/health-health-get",
          label: "Health",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Authentication",
      collapsed: false,
      items: [
        {
          type: "doc",
          id: "api/reference/register-start-auth-register-channel-start-post",
          label: "Register Start",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/reference/register-verify-auth-register-channel-verify-post",
          label: "Register Verify",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/reference/refresh-auth-refresh-post",
          label: "Refresh",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/reference/logout-auth-logout-post",
          label: "Logout",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/reference/me-auth-me-get",
          label: "Me",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/reference/oauth-start-auth-oauth-provider-start-get",
          label: "Oauth Start",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/reference/oauth-callback-auth-oauth-provider-callback-get",
          label: "Oauth Callback",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Admin",
      collapsed: false,
      items: [
        {
          type: "doc",
          id: "api/reference/admin-overview-v-1-admin-overview-get",
          label: "Admin Overview",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Chat Completions",
      collapsed: false,
      items: [
        {
          type: "doc",
          id: "api/reference/chat-completions-v-1-chat-completions-post",
          label: "Chat Completions",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "Embeddings",
      collapsed: false,
      items: [
        {
          type: "doc",
          id: "api/reference/embeddings-v-1-embeddings-post",
          label: "Embeddings",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "API Keys",
      collapsed: false,
      items: [
        {
          type: "doc",
          id: "api/reference/create-key-v-1-keys-post",
          label: "Create Key",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/reference/list-keys-v-1-keys-get",
          label: "List Keys",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Models",
      collapsed: false,
      items: [
        {
          type: "doc",
          id: "api/reference/list-models-v-1-models-get",
          label: "List Models",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Generations",
      collapsed: false,
      items: [
        {
          type: "doc",
          id: "api/reference/get-generation-v-1-generations-generation-id-get",
          label: "Get Generation",
          className: "api-method get",
        },
      ],
    },
  ],
};

export default sidebar.apisidebar;
