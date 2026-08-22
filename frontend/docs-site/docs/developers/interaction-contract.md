# Data masking in the live request path

## What the platform does

Solvable applies request-local masking before a chat request crosses the provider boundary. The current implementation detects common email, phone, payment-card, and Uzbekistan identifier patterns and replaces them with non-sensitive tokens such as `<PII_EMAIL_1>`. The provider adapter receives only the masked message content.

The router restores tokens only in the normalized response returned to the client. The mapping exists only for the lifetime of the request and is not returned by the preview endpoint. Streaming responses are restored chunk by chunk after the provider response has passed through the router.

> Masking reduces exposure; it is not a proof that every sensitive value has been detected. High-risk tenants should combine masking with provider restrictions, blocking policies, retention controls, and human review.

## API contract

Authenticated clients can call `POST https://api.sovable.ai/v1/privacy/preview` with an API key:

```json
{
  "messages": [
    {"role": "user", "content": "Email me at user@example.com or call +998 90 123 45 67."}
  ]
}
```

The response contains masked messages, the number of detected values, token labels, and provider-boundary behavior. It never returns the original sensitive values:

```json
{
  "masked_messages": [
    {"role": "user", "content": "Email me at <PII_EMAIL_1> or call <PII_PHONE_2>."}
  ],
  "detected_count": 2,
  "token_labels": ["EMAIL", "PHONE"],
  "restoration": "request-local; original values are not returned by this endpoint",
  "provider_boundary": "masked content is sent upstream and restored only in normalized client output"
}
```

The production chat path applies the same behavior automatically. Clients do not need to modify their OpenAI-compatible `/v1/chat/completions` request to receive provider-boundary masking. For requests that must not leave approved providers, set `provider.data_collection` to `deny`; routing then excludes providers whose catalog policy allows training on customer data.

## User workflow

The User Portal exposes the privacy surface under **Dashboard → Privacy**. The page includes a live policy check that sends a synthetic example to the authenticated preview endpoint and shows the masked output, detection count, and labels. It does not display raw values returned from the server. A valid API key and healthy gateway are required.

The Organization Admin controls tenant policy, provider eligibility, retention, and audit evidence. The Platform Admin reviews provider policy metadata and routing health. The Agent Creator must declare data scopes and tool permissions before package review.

# Frontend/backend interaction contract

Every visible control must satisfy one of three states: it performs a real API or navigation action, it opens a real documentation or authentication destination, or it is explicitly rendered as informational text without a button affordance. Placeholder alert buttons are not permitted in production surfaces.

| Surface | Public behavior | Authenticated behavior |
|---|---|---|
| Overview and platform pages | Explain capabilities and link to documentation | Portal CTAs route to role-specific sign-in |
| AI App Store catalog | Browse agents, categories, review status, permissions, and pricing | Create routes to Agent Creator; install/open routes to User or Organization Admin |
| Aggregator / Router | Explain masking, routing, fallback, and normalized responses | Playground and policy controls require an authenticated workspace |
| Privacy dashboard | Explain classifications and provider boundary | Masking preview calls `/v1/privacy/preview` with the API-key interceptor |
| Models | Show the live catalog or a retryable error state | API-key authentication is required by the gateway |
| Admin Operations | Explain governance controls | Management-key protected overview and provider/routing operations |
| Platform Controller | No public self-registration | Separate controller authentication and management-key boundary |

## Error and loading requirements

Real API controls must show loading, success, empty, unauthorized, forbidden, rate-limited, and service-unavailable states. A failed request must not be presented as a successful empty result. Navigation that requires a session must preserve a safe same-origin `next` path and return the user to the requested workspace after verification.

## Developer acceptance checks

A change is ready only when the frontend build passes, the corresponding OpenAPI route is present, unauthorized requests return the expected 401/403 boundary, masking tests confirm provider-safe content and response restoration, and the public documentation is regenerated from the current OpenAPI contract.
