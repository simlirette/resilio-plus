const { getDefaultConfig } = require('expo/metro-config');
const { withNativewind } = require('nativewind/metro');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

// Watch all files within the monorepo
config.watchFolders = [workspaceRoot];

// Let Metro know where to resolve packages and in what order
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];

// Force singleton native packages to resolve from the app's node_modules only.
// Prevents pnpm symlinking ui-mobile's own copy → two Metro module IDs → native
// binding registered once but two JS instances → "must be a function (received undefined)".
const SINGLETON_NATIVE_PACKAGES = [
  'react',
  'react-dom',
  'react-native',
  'react-native-svg',
  'react-native-reanimated',
  'react-native-safe-area-context',
  'expo-haptics',
];
config.resolver.extraNodeModules = Object.fromEntries(
  SINGLETON_NATIVE_PACKAGES.map((pkg) => [
    pkg,
    path.resolve(projectRoot, 'node_modules', pkg),
  ])
);

// NativeWind v5 — wraps config to handle CSS/Tailwind transformation
module.exports = withNativewind(config);
