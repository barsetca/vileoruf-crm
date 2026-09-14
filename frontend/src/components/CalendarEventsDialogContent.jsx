import { useTranslation } from "react-i18next";

import CalendarEventsSection from "./CalendarEventsSection.jsx";
import CreateCalendarEventForm from "./CreateCalendarEventForm.jsx";

export default function CalendarEventsDialogContent({
  clientId,
  dealId,
  canCreate = true,
  refreshKey,
  showCreate,
  setShowCreate,
  onAccepted,
}) {
  const { t } = useTranslation();

  return (
    <section className="calendar-events-dialog-content">
      {canCreate && (
        <>
          <button className="secondary-button" type="button" onClick={() => setShowCreate(true)}>
            {t("calendar.create.open")}
          </button>
          {showCreate && (
            <CreateCalendarEventForm
              clientId={clientId}
              dealId={dealId}
              onClose={() => setShowCreate(false)}
              onAccepted={onAccepted}
            />
          )}
        </>
      )}
      <div className="calendar-events-history">
        <CalendarEventsSection clientId={clientId} dealId={dealId} refreshKey={refreshKey} />
      </div>
    </section>
  );
}
