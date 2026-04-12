/**
 * @resilio/ui-web — Icon abstraction layer
 *
 * RULE: Never import lucide-react directly in apps/web or any other package.
 * Always import from @resilio/ui-web instead.
 *
 * This layer provides semantic icon names mapped to lucide-react components,
 * making it easy to swap icon libraries in the future.
 */
import {
  Moon,
  Sun,
  Trash2,
  Plus,
  Minus,
  Calendar,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  AlertTriangle,
  AlertCircle,
  Info,
  Settings,
  User,
  LogOut,
  LogIn,
  Activity,
  BarChart2,
  TrendingUp,
  TrendingDown,
  Clock,
  Zap,
  Heart,
  Target,
  Award,
  Dumbbell,
  Bike,
  Waves,
  Upload,
  Download,
  RefreshCw,
  Edit2,
  Save,
  Link2,
  ExternalLink,
} from 'lucide-react';

export const Icon = {
  // Theme
  DarkMode: Moon,
  LightMode: Sun,

  // Actions
  Add: Plus,
  Remove: Minus,
  Delete: Trash2,
  Edit: Edit2,
  Save: Save,
  Upload: Upload,
  Download: Download,
  Refresh: RefreshCw,
  Link: Link2,
  ExternalLink: ExternalLink,

  // Navigation
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  ChevronUp,

  // Status
  Check,
  Close: X,
  Warning: AlertTriangle,
  Error: AlertCircle,
  Info,

  // UI
  Calendar,
  Settings,
  User,
  LogOut,
  LogIn,

  // Sports / fitness
  Activity,
  Analytics: BarChart2,
  TrendingUp,
  TrendingDown,
  Clock,
  Energy: Zap,
  Heart,
  Target,
  Award,
  Lifting: Dumbbell,
  Biking: Bike,
  Swimming: Waves,
} as const;

export type IconName = keyof typeof Icon;
