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

// Disable hierarchical lookup so Metro does NOT walk up into packages/ui-mobile/node_modules
// when resolving imports from within that package. Instead it uses nodeModulesPaths above,
// which starts with apps/mobile/node_modules — ensuring a single module ID for native
// packages that must have exactly one instance (react-native-svg, reanimated, etc.).
// Without this, pnpm's virtual store creates separate copies per peer-dep context,
// Metro bundles both → native binding registered once → second JS instance is undefined → crash.
config.resolver.disableHierarchicalLookup = true;

// NativeWind v5 — wraps config to handle CSS/Tailwind transformation
module.exports = withNativewind(config);
