export const WHATSAPP_MANAGER_URL = "https://business.facebook.com/wa/manage/phone-numbers/";

const NAME_STATUS_TEXT: Record<string, string> = {
  APPROVED: "Approved",
  PENDING_REVIEW: "In review by Meta",
  DECLINED: "Declined by Meta: edit and resubmit in WhatsApp Manager",
  NONE: "No display name submitted yet",
  AVAILABLE_WITHOUT_REVIEW: "Available without review",
};

/** Plain wording for Meta's name_status; an unknown value is shown as it is. */
export function describeNameStatus(status: string | null | undefined): string {
  if (!status) return "Not checked yet";
  return NAME_STATUS_TEXT[status] ?? status;
}

/** Meta error 131037: the number's display name has not been approved. */
export function isDisplayNameError(lastError: string | null | undefined): boolean {
  return !!lastError && lastError.includes("131037");
}

/** The number's display-name review status, with a pointer to the fix when sends fail because of it. */
export default function DisplayNameStatus({ nameStatus, lastError }: { nameStatus: string | null | undefined; lastError: string | null | undefined }) {
  return (
    <div className="space-y-1 text-sm">
      <p>
        <span className="font-semibold">Display name:</span> {describeNameStatus(nameStatus)}
      </p>
      {isDisplayNameError(lastError) && (
        <p>
          Replies are failing because the display name needs Meta approval (error 131037). Check or resubmit it in{" "}
          <a className="underline" href={WHATSAPP_MANAGER_URL} target="_blank" rel="noopener noreferrer">
            WhatsApp Manager
          </a>
          .
        </p>
      )}
    </div>
  );
}
