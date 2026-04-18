module.exports = function (api) {
  api.cache(true);
  return {
    // NativeWind v5: do NOT add jsxImportSource here (v4 pattern, removed in v5)
    // Explicit router.appRoot forces expo-router's Babel transform to inject
    // EXPO_ROUTER_APP_ROOT, bypassing pnpm resolution issues in the monorepo.
    presets: [
      ['babel-preset-expo', { router: { appRoot: 'app' } }]
    ],
  };
};
