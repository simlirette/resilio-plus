/**
 * Mock for react-native-safe-area-context.
 * Returns zero insets so Screen component can render without native context.
 */
export const useSafeAreaInsets = jest.fn().mockReturnValue({
  top: 0,
  bottom: 0,
  left: 0,
  right: 0,
});

export const SafeAreaProvider = ({ children }: { children: React.ReactNode }) => children;
export const SafeAreaView = ({ children }: { children: React.ReactNode }) => children;
export const SafeAreaConsumer = ({ children }: { children: Function }) =>
  children({ top: 0, bottom: 0, left: 0, right: 0 });
