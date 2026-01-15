# AI Chatbot Frontend

Modern Next.js frontend for the AI Chatbot application.

## Features

- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** components for UI
- **Real-time chat interface** with streaming support
- **Source citations** and confidence scores
- **Conversation management**

## Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running on `http://localhost:5000` (or configure `NEXT_PUBLIC_API_URL`)

## Setup

1. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

2. Configure the API URL (optional):
   - Create a `.env.local` file in the `frontend` directory
   - Add: `NEXT_PUBLIC_API_URL=http://localhost:5000`
   - Or set it as an environment variable

3. Run the development server:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   └── globals.css        # Global styles
├── components/
│   ├── ui/                # shadcn/ui components
│   └── AIAssistant.tsx   # Main chat component
├── lib/
│   ├── api.ts            # API client
│   └── utils.ts          # Utility functions
└── hooks/
    └── use-toast.ts      # Toast notification hook
```

## API Integration

The frontend connects to the backend API at `/api/ai/chat`. Make sure the backend is running and CORS is properly configured.

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: `http://localhost:5000`)
