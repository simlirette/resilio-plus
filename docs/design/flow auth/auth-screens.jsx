// Resilio+ Auth Screens — Login, Signup, Forgot Password
// Light + Dark variants

const RESILIO = {
  light: {
    bg: '#F5F5F2',
    surface: '#FAFAF7',
    text: '#1A1A17',
    textSecondary: '#6B6862',
    textTertiary: '#9A968D',
    border: '#E3E0D8',
    borderStrong: '#D4D0C6',
    accent: 'oklch(0.62 0.14 35)',       // warm amber
    accentPressed: 'oklch(0.56 0.14 35)',
    onAccent: '#FAFAF7',
    divider: '#E8E6E0',
    apple: '#000000',
    appleText: '#FFFFFF',
  },
  dark: {
    bg: '#17171A',                         // warm charbon (not clinical)
    surface: '#1F1F22',
    text: '#F0EEE8',
    textSecondary: '#9E9A90',
    textTertiary: '#6B6862',
    border: '#2E2D2A',
    borderStrong: '#3A3834',
    accent: 'oklch(0.68 0.13 38)',         // slightly brighter for dark
    accentPressed: 'oklch(0.62 0.13 38)',
    onAccent: '#17171A',
    divider: '#262523',
    apple: '#FFFFFF',
    appleText: '#000000',
  },
};

const FONT = "'Space Grotesk', -apple-system, system-ui, sans-serif";
const FONT_MONO = "'Space Grotesk', ui-monospace, monospace";

// ─────────────────────────────────────────────────────────────
// Wordmark — pure type, small, centered
// ─────────────────────────────────────────────────────────────
function Wordmark({ theme }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', justifyContent: 'center',
      gap: 0, fontFamily: FONT, fontWeight: 600,
      fontSize: 17, letterSpacing: -0.3, color: theme.text,
    }}>
      <span>Resilio</span>
      <span style={{ color: theme.accent, fontWeight: 500 }}>+</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Floating-label input — Material-style épuré
// ─────────────────────────────────────────────────────────────
function Input({ label, type = 'text', value, onChange, theme, onToggleSecure, secure, autoFocus, focused: forceFocused }) {
  const [focused, setFocused] = React.useState(false);
  const isFocused = forceFocused !== undefined ? forceFocused : focused;
  const hasValue = value && value.length > 0;
  const floating = isFocused || hasValue;

  const borderColor = isFocused ? theme.accent : theme.border;
  const borderWidth = isFocused ? 1.5 : 1;

  return (
    <div style={{
      position: 'relative',
      height: 56,
      background: 'transparent',
      borderRadius: 10,
      border: `${borderWidth}px solid ${borderColor}`,
      transition: 'border-color 120ms ease, border-width 120ms ease',
      display: 'flex', alignItems: 'center',
      paddingLeft: 14, paddingRight: 14,
      // compensate padding when border grows
      margin: isFocused ? '-0.5px' : 0,
    }}>
      {/* label */}
      <label style={{
        position: 'absolute',
        left: 13,
        top: floating ? -7 : '50%',
        transform: floating ? 'translateY(0)' : 'translateY(-50%)',
        fontFamily: FONT,
        fontSize: floating ? 11 : 15,
        fontWeight: floating ? 500 : 400,
        letterSpacing: floating ? 0.4 : 0,
        textTransform: floating ? 'uppercase' : 'none',
        color: floating
          ? (isFocused ? theme.accent : theme.textSecondary)
          : theme.textTertiary,
        background: theme.bg,
        padding: floating ? '0 6px' : '0',
        pointerEvents: 'none',
        transition: 'all 140ms ease',
      }}>{label}</label>

      <input
        type={secure && type === 'password' ? 'password' : (type === 'password' ? 'text' : type)}
        value={value || ''}
        onChange={(e) => onChange && onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        autoFocus={autoFocus}
        style={{
          flex: 1, height: '100%',
          background: 'transparent', border: 'none', outline: 'none',
          fontFamily: FONT, fontSize: 16, fontWeight: 400,
          color: theme.text, letterSpacing: -0.1,
          padding: 0,
        }}
      />

      {onToggleSecure && (
        <button
          onClick={onToggleSecure}
          style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            padding: 6, display: 'flex', alignItems: 'center',
            color: theme.textSecondary,
          }}
        >
          {secure ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M2 10s3-6 8-6 8 6 8 6-3 6-8 6-8-6-8-6z" stroke="currentColor" strokeWidth="1.4"/>
              <circle cx="10" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.4"/>
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M3 3l14 14M8 4.5A8 8 0 0118 10s-1 2-3 3.5M12 15.5A8 8 0 012 10s1-2 3-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
              <path d="M7.5 7.5a3.5 3.5 0 005 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
          )}
        </button>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Buttons
// ─────────────────────────────────────────────────────────────
function PrimaryButton({ label, theme, onClick, disabled, loading }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        width: '100%', height: 54,
        background: disabled ? theme.borderStrong : theme.accent,
        color: theme.onAccent,
        border: 'none', borderRadius: 12,
        fontFamily: FONT, fontSize: 16, fontWeight: 500,
        letterSpacing: -0.1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'background 120ms ease, transform 80ms ease',
      }}
    >
      {loading ? (
        <div style={{
          width: 18, height: 18, borderRadius: '50%',
          border: `2px solid ${theme.onAccent}`,
          borderTopColor: 'transparent',
          animation: 'resilio-spin 0.7s linear infinite',
        }} />
      ) : label}
    </button>
  );
}

function AppleButton({ theme, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%', height: 54,
        background: theme.apple, color: theme.appleText,
        border: 'none', borderRadius: 12,
        fontFamily: FONT, fontSize: 16, fontWeight: 500,
        letterSpacing: -0.1,
        cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 8,
      }}
    >
      <svg width="16" height="20" viewBox="0 0 16 20" fill="currentColor" style={{ marginTop: -2 }}>
        <path d="M13.4 10.6c0-2.4 2-3.5 2.1-3.6-1.1-1.6-2.9-1.9-3.5-1.9-1.5-.2-2.9.9-3.7.9-.8 0-1.9-.9-3.2-.8C3.4 5.3 2 6.2 1.2 7.6c-1.7 3-.4 7.4 1.2 9.8.8 1.2 1.8 2.5 3.1 2.4 1.2 0 1.7-.8 3.2-.8 1.5 0 1.9.8 3.2.8 1.3 0 2.2-1.2 3-2.4.9-1.4 1.3-2.7 1.3-2.8-.1 0-2.6-1-2.6-4zm-2.5-7.4C11.6 2.4 12 1.3 11.9 0c-1.1 0-2.4.7-3.2 1.6C8 2.4 7.4 3.6 7.6 4.7c1.2.1 2.4-.6 3.3-1.5z"/>
      </svg>
      Continuer avec Apple
    </button>
  );
}

function SecondaryButton({ label, theme, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%', height: 54,
        background: 'transparent', color: theme.text,
        border: `1px solid ${theme.borderStrong}`, borderRadius: 12,
        fontFamily: FONT, fontSize: 16, fontWeight: 500,
        letterSpacing: -0.1,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );
}

function LinkText({ label, theme, onClick, accent = false, size = 14 }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'transparent', border: 'none', padding: 0,
        fontFamily: FONT, fontSize: size, fontWeight: 500,
        color: accent ? theme.accent : theme.textSecondary,
        cursor: 'pointer', letterSpacing: -0.1,
      }}
    >
      {label}
    </button>
  );
}

function Divider({ theme, label = 'ou' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{ flex: 1, height: 1, background: theme.divider }} />
      <span style={{
        fontFamily: FONT, fontSize: 12, fontWeight: 500,
        color: theme.textTertiary, letterSpacing: 0.5,
        textTransform: 'uppercase',
      }}>{label}</span>
      <div style={{ flex: 1, height: 1, background: theme.divider }} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Screen wrapper
// ─────────────────────────────────────────────────────────────
function ScreenBody({ theme, children }) {
  return (
    <div style={{
      height: '100%', width: '100%',
      background: theme.bg, color: theme.text,
      display: 'flex', flexDirection: 'column',
      fontFamily: FONT,
      WebkitFontSmoothing: 'antialiased',
    }}>
      {children}
    </div>
  );
}

function ScreenHeader({ theme, title, subtitle, onBack }) {
  return (
    <div style={{ padding: '20px 24px 0' }}>
      {/* wordmark bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 44, position: 'relative', marginBottom: 48,
      }}>
        {onBack && (
          <button
            onClick={onBack}
            style={{
              position: 'absolute', left: 0,
              background: 'transparent', border: 'none', padding: 8,
              display: 'flex', alignItems: 'center',
              color: theme.textSecondary, cursor: 'pointer',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <path d="M14 4l-7 7 7 7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        )}
        <Wordmark theme={theme} />
      </div>

      {/* title block */}
      <div style={{ marginBottom: 36 }}>
        <h1 style={{
          fontFamily: FONT, fontWeight: 500, fontSize: 32,
          letterSpacing: -1.2, lineHeight: 1.08,
          margin: 0, color: theme.text,
          fontVariantNumeric: 'tabular-nums',
        }}>{title}</h1>
        {subtitle && (
          <p style={{
            fontFamily: FONT, fontWeight: 400, fontSize: 15,
            lineHeight: 1.45, letterSpacing: -0.1,
            margin: '10px 0 0', color: theme.textSecondary,
            maxWidth: 320,
          }}>{subtitle}</p>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// LOGIN
// ─────────────────────────────────────────────────────────────
function LoginScreen({ theme, onNavigate, prefill }) {
  const [email, setEmail] = React.useState(prefill?.email || '');
  const [password, setPassword] = React.useState(prefill?.password || '');
  const [secure, setSecure] = React.useState(true);

  return (
    <ScreenBody theme={theme}>
      <ScreenHeader theme={theme} title="Connexion" />

      <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Input label="Email" type="email" value={email} onChange={setEmail} theme={theme}
          focused={prefill?.focusEmail} />
        <Input label="Mot de passe" type="password" value={password} onChange={setPassword}
          theme={theme} secure={secure} onToggleSecure={() => setSecure(!secure)}
          focused={prefill?.focusPassword}/>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 2 }}>
          <LinkText label="Mot de passe oublié" theme={theme} accent
            onClick={() => onNavigate && onNavigate('forgot')} />
        </div>
      </div>

      <div style={{ padding: '24px 24px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <PrimaryButton label="Se connecter" theme={theme} loading={prefill?.loading} />
        <Divider theme={theme} />
        <AppleButton theme={theme} />
      </div>

      <div style={{ flex: 1 }} />

      <div style={{
        padding: '20px 24px 36px',
        display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 6,
      }}>
        <span style={{
          fontFamily: FONT, fontSize: 14, color: theme.textSecondary,
          letterSpacing: -0.1,
        }}>Pas de compte ?</span>
        <LinkText label="Créer un compte" theme={theme} accent
          onClick={() => onNavigate && onNavigate('signup')} />
      </div>
    </ScreenBody>
  );
}

// ─────────────────────────────────────────────────────────────
// SIGNUP
// ─────────────────────────────────────────────────────────────
function SignupScreen({ theme, onNavigate, prefill }) {
  const [email, setEmail] = React.useState(prefill?.email || '');
  const [password, setPassword] = React.useState(prefill?.password || '');
  const [confirm, setConfirm] = React.useState(prefill?.confirm || '');
  const [secure, setSecure] = React.useState(true);
  const [secure2, setSecure2] = React.useState(true);

  return (
    <ScreenBody theme={theme}>
      <ScreenHeader theme={theme} title="Créer un compte" onBack={() => onNavigate && onNavigate('login')} />

      <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Input label="Email" type="email" value={email} onChange={setEmail} theme={theme} />
        <Input label="Mot de passe" type="password" value={password} onChange={setPassword}
          theme={theme} secure={secure} onToggleSecure={() => setSecure(!secure)} />
        <Input label="Confirmer le mot de passe" type="password" value={confirm} onChange={setConfirm}
          theme={theme} secure={secure2} onToggleSecure={() => setSecure2(!secure2)} />
      </div>

      <div style={{ padding: '24px 24px 0', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <PrimaryButton label="Créer mon compte" theme={theme} />
        <p style={{
          fontFamily: FONT, fontSize: 12, lineHeight: 1.45,
          color: theme.textTertiary, letterSpacing: -0.05,
          margin: 0, textAlign: 'center',
        }}>
          En créant un compte, tu acceptes les{' '}
          <span style={{ color: theme.textSecondary, textDecoration: 'underline', textDecorationColor: theme.border }}>
            conditions d'utilisation
          </span>
          {' '}et la{' '}
          <span style={{ color: theme.textSecondary, textDecoration: 'underline', textDecorationColor: theme.border }}>
            politique de confidentialité
          </span>.
        </p>
        <div style={{ marginTop: 6 }}>
          <Divider theme={theme} />
        </div>
        <AppleButton theme={theme} />
      </div>

      <div style={{ flex: 1 }} />

      <div style={{
        padding: '20px 24px 36px',
        display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 6,
      }}>
        <span style={{ fontFamily: FONT, fontSize: 14, color: theme.textSecondary }}>
          Déjà un compte ?
        </span>
        <LinkText label="Se connecter" theme={theme} accent
          onClick={() => onNavigate && onNavigate('login')} />
      </div>
    </ScreenBody>
  );
}

// ─────────────────────────────────────────────────────────────
// FORGOT PASSWORD
// ─────────────────────────────────────────────────────────────
function ForgotScreen({ theme, onNavigate, prefill }) {
  const [email, setEmail] = React.useState(prefill?.email || '');
  const [sent, setSent] = React.useState(prefill?.sent || false);

  return (
    <ScreenBody theme={theme}>
      <ScreenHeader
        theme={theme}
        title="Réinitialiser le mot de passe"
        subtitle={sent
          ? `Un lien a été envoyé à ${email}. Vérifie ta boîte de réception et le dossier spam.`
          : "Entre ton email, on t'envoie un lien."}
        onBack={() => onNavigate && onNavigate('login')}
      />

      {!sent && (
        <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Input label="Email" type="email" value={email} onChange={setEmail} theme={theme} />
        </div>
      )}

      {sent && (
        <div style={{ padding: '0 24px' }}>
          <div style={{
            padding: '16px 18px',
            border: `1px solid ${theme.border}`,
            borderRadius: 12,
            display: 'flex', gap: 12, alignItems: 'flex-start',
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: theme.surface,
              border: `1px solid ${theme.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, color: theme.accent,
            }}>
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <rect x="2" y="4" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
                <path d="M2 5l7 5 7-5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{
                fontFamily: FONT, fontSize: 13, fontWeight: 500,
                color: theme.text, letterSpacing: -0.1,
              }}>Email envoyé</div>
              <div style={{
                fontFamily: FONT, fontSize: 13, color: theme.textSecondary,
                marginTop: 2, letterSpacing: -0.05,
              }}>Expire dans 30 minutes.</div>
            </div>
          </div>
        </div>
      )}

      <div style={{ padding: '24px 24px 0', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {!sent ? (
          <PrimaryButton label="Envoyer le lien" theme={theme} onClick={() => setSent(true)} />
        ) : (
          <SecondaryButton label="Renvoyer" theme={theme} onClick={() => setSent(false)} />
        )}
      </div>

      <div style={{ flex: 1 }} />

      <div style={{
        padding: '20px 24px 36px',
        display: 'flex', justifyContent: 'center', alignItems: 'center',
      }}>
        <LinkText label="Revenir à la connexion" theme={theme} accent
          onClick={() => onNavigate && onNavigate('login')} />
      </div>
    </ScreenBody>
  );
}

Object.assign(window, {
  RESILIO, FONT, Wordmark, Input, PrimaryButton, AppleButton, SecondaryButton,
  LinkText, Divider, ScreenBody, ScreenHeader,
  LoginScreen, SignupScreen, ForgotScreen,
});
