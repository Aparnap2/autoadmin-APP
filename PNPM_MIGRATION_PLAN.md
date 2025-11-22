# AutoAdmin pnpm & Firebase Functions Migration Plan

## Current Status Analysis ✅

### Already Completed:
- ✅ pnpm workspace configured (`pnpm-workspace.yaml`)
- ✅ pnpm-lockfile exists
- ✅ Netlify Functions structure in place (`/app/api/`)
- ✅ Firebase database (Firestore) services configured
- ✅ Firebase Functions dependencies not found in package.json
- ✅ `/functions/` directory doesn't exist

### Tasks to Complete:

## 1. Clean Up Firebase Functions References
- [ ] Remove `functionsService` references from graph-memory.ts
- [ ] Update any remaining Firebase Functions imports
- [ ] Remove Firebase Functions from environment variables

## 2. Finalize pnpm Configuration
- [ ] Update package.json scripts to use pnpm commands
- [ ] Create `.pnpmrc` configuration for performance
- [ ] Update netlify.toml build commands to use pnpm
- [ ] Remove any npm/yarn lockfiles if they exist

## 3. Update Vector Search API Routes
- [ ] Ensure `/app/api/vector/search/route.ts` uses OpenAI directly
- [ ] Verify `/app/api/vector/embeddings/route.ts` implementation
- [ ] Add proper error handling and OpenAI integration

## 4. Complete Graph Operations Migration
- [ ] Verify `/app/api/graph/subgraph/route.ts` implementation
- [ ] Verify `/app/api/graph/traversal/route.ts` implementation
- [ ] Update services to use Netlify API routes instead of Firebase Functions

## 5. Update Configuration Files
- [ ] Update `.env.example` to remove Firebase Functions variables
- [ ] Ensure `firebase.json` only contains database/hosting rules
- [ ] Update `netlify.toml` for pnpm build commands

## 6. Services Migration
- [ ] Update `services/agents/` to use Netlify Functions only
- [ ] Update `services/delegation/` to use Netlify API
- [ ] Ensure all serverless operations go through `/app/api/`

## 7. Testing & Validation
- [ ] Test all API routes work correctly
- [ ] Verify authentication with Firebase Auth works
- [ ] Test vector search functionality
- [ ] Test graph operations
- [ ] Test agent triggers via Netlify Functions

## Final Architecture:
- **Frontend**: Expo SDK 54 + pnpm + Firebase (Auth, Firestore, Storage only)
- **Serverless**: Netlify Functions only
- **Database**: Firebase Firestore only
- **Backend**: GitHub Actions for heavy tasks