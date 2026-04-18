// Runs before Jest environment — sets env vars needed before test modules load.
// Skips @testing-library/react-native exact version peer-dep check which fails
// in pnpm monorepos where React versions are resolved from different hoisting contexts.
process.env['RNTL_SKIP_DEPS_CHECK'] = 'true';
