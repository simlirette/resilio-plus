// jest setup for @resilio/ui-mobile
// Runs after Jest environment is initialized (setupFilesAfterEnv)
// @testing-library/react-native v13 includes jest matchers automatically

// Skip the react/react-test-renderer exact-version peer-dep check.
// In a pnpm monorepo two React versions may be hoisted differently in different
// package contexts; the versions are functionally compatible (19.x) and the
// mismatch is a resolution artefact, not a real incompatibility.
process.env['RNTL_SKIP_DEPS_CHECK'] = 'true';
