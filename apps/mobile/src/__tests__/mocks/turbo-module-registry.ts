/**
 * TurboModuleRegistry mock for RN 0.83.x jest environment.
 *
 * RN 0.83 introduced ReactNativeFeatureFlags which uses TurboModuleRegistry
 * at StyleSheet initialization time. This mock provides safe defaults to prevent
 * "__fbBatchedBridgeConfig is not set" and "Cannot read properties of undefined (reading 'screen')".
 *
 * Call chain that crashes without this mock:
 *   StyleSheet → StyleSheetExports → PixelRatio → Dimensions → NativeDimensions
 *   → TurboModuleRegistry.get('Dimensions').getConstants() → crash
 *
 * AND:
 *   StyleSheet → ReactNativeStyleAttributes → ReactNativeFeatureFlags
 *   → TurboModuleRegistry.getEnforcing('ReactNativeFeatureFlags').getConstants() → crash
 */

const WINDOW_DIMENSIONS = { width: 390, height: 844, scale: 2, fontScale: 1 };

function makeMockModule() {
  return {
    getConstants: () => ({
      window: WINDOW_DIMENSIONS,
      screen: WINDOW_DIMENSIONS,
    }),
    addListener: () => {},
    removeListeners: () => {},
  };
}

module.exports = {
  get: (_name: string) => makeMockModule(),
  getEnforcing: (_name: string) => makeMockModule(),
};
