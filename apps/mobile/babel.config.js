module.exports = function (api) {
  api.cache(true);
  return {
    // NativeWind v5: do NOT add jsxImportSource here (v4 pattern, removed in v5)
    presets: ['babel-preset-expo'],
  };
};
