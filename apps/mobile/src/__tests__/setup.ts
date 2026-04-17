/**
 * Jest setup for apps/mobile component tests.
 *
 * React Native 0.83.x: NativeModules and TurboModuleRegistry are mocked by
 * react-native's own jest preset (react-native/jest/setup.js), which runs as
 * a setupFile before this file. That preset provides correct mocks including
 * DeviceInfo.getConstants() → { Dimensions: { window, screen } }.
 *
 * The unified react-native instance (via moduleNameMapper in jest.app.config.js)
 * ensures all packages use the same react-native, so the preset mocks apply everywhere.
 *
 * Do NOT add TurboModuleRegistry mocks here — they override the correct preset mocks
 * and break Dimensions initialization (NativeDeviceInfo expects { Dimensions: {...} }
 * but a naïve mock returns { window, screen } directly).
 */
