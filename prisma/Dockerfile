FROM node:20-alpine
RUN npm install -g pnpm@9

WORKDIR /app
COPY \
	pnpm-workspace.yaml \
	package.json \
	pnpm-lock.yaml \
	.npmrc \
	./
COPY prisma/ ./prisma/

RUN	--mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
	pnpm install --frozen-lockfile \
	| grep -v "cross-device link not permitted\|Falling back to copying packages from store"
	# ↑ This inverted grep match is because using Docker's 'cache' mount type
	# causes Docker to place the pnpm content-addressable store on a different virtual drive,
	# which prohibits pnpm from symlinking its content to its virtual store (in node_modules/.pnpm),
	# and that causes pnpm to fall back on copying the files. And that's fine,
	# except pnpm emits a lot of warnings doing that, so here we filter out those warnings.

ENTRYPOINT ["pnpm", "exec", "prisma", "studio", "dev"]
