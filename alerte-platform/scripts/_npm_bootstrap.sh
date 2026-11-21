#!/usr/bin/env bash
# Installe les dépendances du frontend avec le Node géré par nvm (jamais de sudo).
set -euo pipefail
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
# shellcheck disable=SC1091
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null
cd "$(dirname "$0")/../frontend"
npm install
npm install react-router-dom @tanstack/react-query react-hook-form zod @hookform/resolvers lucide-react clsx
npm install -D tailwindcss @tailwindcss/vite vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event openapi-typescript
