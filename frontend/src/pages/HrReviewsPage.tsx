import { HrReviewPanel } from "../features/reviews";
import type { AppControllerContext } from "../app/types";

interface HrReviewsPageProps
  extends Pick<
    AppControllerContext,
    "activeSection" | "dataScope" | "hrReviews" | "isHr"
  > {
  acceptError: string | null;
  activeProfileId: AppControllerContext["hrDecisionProfileId"];
  bulkActive: boolean;
  bulkError: string | null;
  message: AppControllerContext["hrDecisionMessage"];
  onAccept: AppControllerContext["acceptByHr"];
  onBulkReturnSelected: AppControllerContext["bulkReturnByHrSelected"];
  onBulkReturnUnit: AppControllerContext["bulkReturnByHrUnit"];
  onReturn: AppControllerContext["returnByHr"];
  returnError: string | null;
}

export function HrReviewsPage({
  acceptError,
  activeProfileId,
  activeSection,
  bulkActive,
  bulkError,
  dataScope,
  hrReviews,
  isHr,
  message,
  onAccept,
  onBulkReturnSelected,
  onBulkReturnUnit,
  onReturn,
  returnError,
}: HrReviewsPageProps) {
  if (!isHr || activeSection !== "hr-reviews") return null;
  if (dataScope !== "work" && dataScope !== "demo") return null;

  return (
    <HrReviewPanel
      activeProfileId={activeProfileId}
      bulkActive={bulkActive}
      error={acceptError ?? returnError ?? bulkError ?? null}
      message={message}
      onAccept={onAccept}
      onBulkReturnSelected={onBulkReturnSelected}
      onBulkReturnUnit={onBulkReturnUnit}
      onReturn={onReturn}
      reviews={hrReviews.data ?? []}
    />
  );
}
