<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:81ccb5451edcb5de1ae339657ec8f32e1acdd937c98a07711296da0885fd2768 -->

# Orbit storefront

A responsive React storefront with five sample products, details, search, filters, sorting, a shopping bag, and simulated USDT, SOL, and card checkout.

## Run

```sh
npm install
npm run dev -- --port 3000
```

Build: `npm run build`. Serve the build: `npm run preview`. Verified using Node 24.21.0 and npm 11.19.0.

## Demo boundaries

Checkout simulates payment and creates an order in browser memory for the current session. Refreshing resets orders and the cart. No funds move, card details are not collected, and no wallet connects. Telegram buttons explain the pending integration.

Live operation requires a backend with persisted orders, authenticated Telegram bot integration, a card provider, crypto invoice creation and verified settlement, and validated payment webhooks before fulfillment. Keep provider credentials out of frontend code.

Product photos load from Unsplash and fonts from Google Fonts.


<!-- /coderabbit-ai-generated:v1 -->