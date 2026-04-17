/**
 * Mock for react-native-svg.
 * Each SVG primitive renders as a plain View to allow render-level testing.
 */
import React from 'react';
import { View } from 'react-native';

const SvgMock = (props: object) => <View {...props} />;

export default SvgMock;
export const Svg = SvgMock;
export const Circle = SvgMock;
export const Rect = SvgMock;
export const Path = SvgMock;
export const G = SvgMock;
export const Text = SvgMock;
export const Line = SvgMock;
export const Polyline = SvgMock;
export const Polygon = SvgMock;
export const Ellipse = SvgMock;
