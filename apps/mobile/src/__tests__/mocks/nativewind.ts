/**
 * NativeWind jest mock — no-op for test environment.
 * NativeWind patches react-native components at import time to support className.
 * In tests, className is passed as a prop but doesn't need to be processed.
 */
export const cssInterop = jest.fn();
export const remapProps = jest.fn();
export const withExoticComponent = (component: unknown) => component;
export const useColorScheme = () => ({ colorScheme: 'dark', setColorScheme: jest.fn() });
export const useUnstableNativeVariable = () => undefined;
export default { cssInterop, remapProps, withExoticComponent, useColorScheme };
