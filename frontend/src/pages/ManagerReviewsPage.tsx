import { ManagerReviewPanel } from "../features/manager";
import type { AppControllerContext } from "../app/types";

interface ManagerReviewsPageProps
  extends Pick<
    AppControllerContext,
    "activeSection" | "isManager" | "managerReviews"
  > {
  activeProfileId: AppControllerContext["reviewActionProfileId"];
  bulkActive: boolean;
  bulkError: string | null;
  message: AppControllerContext["reviewMessage"];
  onBulkReturnSelected: AppControllerContext["bulkReturnReviewSelected"];
  onBulkReturnUnit: AppControllerContext["bulkReturnReviewUnit"];
  onReturn: AppControllerContext["returnReview"];
  onTake: AppControllerContext["takeReview"];
  onVerify: AppControllerContext["verifyReview"];
  returnError: string | null;
  takeError: string | null;
  verifyError: string | null;
}

export function ManagerReviewsPage({
  activeProfileId,
  activeSection,
  bulkActive,
  bulkError,
  isManager,
  managerReviews,
  message,
  onBulkReturnSelected,
  onBulkReturnUnit,
  onReturn,
  onTake,
  onVerify,
  returnError,
  takeError,
  verifyError,
}: ManagerReviewsPageProps) {
  if (!isManager || activeSection !== "manager-reviews") return null;

  return (
    <ManagerReviewPanel
      activeProfileId={activeProfileId}
      bulkActive={bulkActive}
      error={takeError ?? returnError ?? bulkError ?? verifyError ?? null}
      message={message}
      onBulkReturnSelected={onBulkReturnSelected}
      onBulkReturnUnit={onBulkReturnUnit}
      onReturn={onReturn}
      onTake={onTake}
      onVerify={onVerify}
      reviews={managerReviews.data ?? []}
    />
  );
}
