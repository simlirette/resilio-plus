/**
 * @resilio/ui-mobile — Icon abstraction layer (React Native / Expo)
 *
 * RULE: Never import lucide-react-native directly in apps/mobile.
 * Always import from @resilio/ui-mobile instead.
 *
 * Mirror of @resilio/ui-web/src/icons.ts — same semantic names, RN source.
 */
import {
  Moon, Sun, Trash2, Plus, Minus, Calendar, ChevronRight, ChevronLeft,
  ChevronDown, ChevronUp, Check, X, AlertTriangle, AlertCircle, Info,
  Settings, User, LogOut, LogIn, Activity, BarChart2, TrendingUp, TrendingDown,
  Clock, Zap, Heart, Target, Award, Dumbbell, Bike, Waves,
  Upload, Download, RefreshCw, Edit2, Save, Link2, ExternalLink,
} from 'lucide-react-native';

export const Icon = {
  DarkMode: Moon, LightMode: Sun,
  Add: Plus, Remove: Minus, Delete: Trash2, Edit: Edit2, Save: Save,
  Upload: Upload, Download: Download, Refresh: RefreshCw, Link: Link2, ExternalLink: ExternalLink,
  ChevronRight, ChevronLeft, ChevronDown, ChevronUp,
  Check, Close: X, Warning: AlertTriangle, Error: AlertCircle, Info,
  Calendar, Settings, User, LogOut, LogIn,
  Activity, Analytics: BarChart2, TrendingUp, TrendingDown, Clock,
  Energy: Zap, Heart, Target, Award, Lifting: Dumbbell, Biking: Bike, Swimming: Waves,
} as const;

export type IconName = keyof typeof Icon;
