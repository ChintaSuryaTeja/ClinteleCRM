import { ButtonLink, EmptyState, PageTitle } from "@/components/ui";

export default function CustomerNotFound() {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Customer not found</PageTitle>
      <div className="mt-8">
        <EmptyState title="There's no customer at this address">
          <p>The link may be mistyped, or the customer belongs to another organization.</p>
          <ButtonLink href="/customers" variant="secondary" className="mt-6">
            Go to all customers
          </ButtonLink>
        </EmptyState>
      </div>
    </div>
  );
}
