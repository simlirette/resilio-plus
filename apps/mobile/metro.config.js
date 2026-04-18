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

// Force singleton native packages to always resolve from apps/mobile/node_modules.
// pnpm creates separate virtual store entries per peer-dep context (peer#bb03 for
// apps/mobile, peer#0d2d for ui-mobile). Metro follows symlinks → two distinct file
// paths → two module IDs → native binding registered once → second instance undefined.
//
// resolveRequest intercepts BEFORE nodeModulesPaths traversal. By faking originModulePath
// to be inside apps/mobile, Metro's hierarchical lookup starts at apps/mobile/node_modules
// and finds the single canonical copy.
//
// Note: disableHierarchicalLookup:true is too broad — it breaks transitive deps
// (e.g. whatwg-fetch) that only live in pnpm virtual store sub-paths.
const SINGLETON_NATIVE_PACKAGES = new Set([
  'react',
  'react-dom',
  'react-native',
  'react-native-svg',
  'react-native-reanimated',
  'react-native-safe-area-context',
  'expo-haptics',
]);

config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (SINGLETON_NATIVE_PACKAGES.has(moduleName)) {
    return context.resolveRequest(
      { ...context, originModulePath: path.resolve(projectRoot, 'package.json') },
      moduleName,
      platform
    );
  }
  return context.resolveRequest(context, moduleName, platform);
};

// NativeWind v5 — wraps config to handle CSS/Tailwind transformation
module.exports = withNativewind(config);
