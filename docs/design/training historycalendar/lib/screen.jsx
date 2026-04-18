// Resilio+ — Training history screen

function Screen({ mode, view, initialDayKey }) {
  const theme = window.THEMES[mode];
  const [currentView, setView] = React.useState(view);
  const [selectedDay, setSelectedDay] = React.useState(initialDayKey || null);
  const [selectedSession, setSelectedSession] = React.useState(null);

  React.useEffect(() => setView(view), [view]);

  return (
    <div style={{
      height: '100%',
      background: theme.bg,
      display: 'flex', flexDirection: 'column',
      color: theme.text,
      fontFamily: 'Space Grotesk',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        paddingTop: 54,
        paddingLeft: 20, paddingRight: 20,
        paddingBottom: 14,
        background: theme.bg,
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: 16,
        }}>
          <div style={{
            fontFamily: 'Space Grotesk',
            fontSize: 28, fontWeight: 500,
            letterSpacing: -0.8, color: theme.text,
          }}>Entraînement</div>
          <button style={{
            width: 34, height: 34, borderRadius: 10,
            background: theme.surface2,
            border: 'none', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: theme.textSec,
          }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 3h12M3 7h8M5 11h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* Segmented */}
        <Segmented
          options={[
            { value: 'cal', label: 'Calendrier' },
            { value: 'list', label: 'Liste' },
          ]}
          value={currentView}
          onChange={setView}
          theme={theme}
        />
      </div>

      {/* Stats Strip */}
      <StatsStrip theme={theme} />

      {/* Scrollable content */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        background: theme.bg,
      }}>
        {currentView === 'cal' ? (
          <CalendarView
            theme={theme}
            monthOffset={0}
            onSelectDay={setSelectedDay}
            selectedDayKey={selectedDay}
          />
        ) : (
          <ListView theme={theme} onSelectSession={(s) => setSelectedDay(s.dateKey)} />
        )}
      </div>

      {/* Day detail drawer */}
      {selectedDay && (
        <DayDetail
          dayKey={selectedDay}
          theme={theme}
          onClose={() => setSelectedDay(null)}
        />
      )}
    </div>
  );
}

window.Screen = Screen;
