import {
  Alert,
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  Text,
  useInsights,
} from '@insights-platform/ui-kit';
import type { DataTableColumn, InsightRow } from '@insights-platform/ui-kit';
import { API_BASE_URL, DATASET_LABEL } from './config';

const columns: DataTableColumn<InsightRow>[] = [
  { key: 'metric', header: 'Metric' },
  {
    key: 'period',
    header: 'Period',
    width: '160px',
    render: (row) => (
      <Text size="sm" tone="muted" as="span" mono>
        {row.period}
      </Text>
    ),
  },
  {
    key: 'value',
    header: 'Value',
    align: 'right',
    width: '160px',
    render: (row) => (
      <Text as="span" weight="medium" mono>
        {row.value}
      </Text>
    ),
  },
];

export interface CompensationPageProps {
  token: string | null;
  onSessionExpired: () => void;
}

/**
 * The dashboard's one page.
 *
 * It is deliberately trivial. This app exists to show that a tenant frontend is
 * a thin consumer of the platform — not to demonstrate reporting features.
 */
export function CompensationPage({
  token,
  onSessionExpired,
}: CompensationPageProps) {
  const insights = useInsights({
    token,
    apiUrl: API_BASE_URL,
    onUnauthorized: onSessionExpired,
  });

  return (
    <>
      {insights.status === 'error' ? (
        <Alert
          tone="danger"
          title="Could not load compensation metrics"
          className="page-alert"
          action={
            <Button size="sm" variant="secondary" onClick={insights.refresh}>
              Retry
            </Button>
          }
        >
          {insights.error}{' '}
          {/* ADR-2: on the restricted tier an unrecordable access is refused
              outright, so a 503 here is the audit sink, not the warehouse. */}
          On this tier a failure to record an access blocks the access, so a
          temporary outage can look like missing data.
        </Alert>
      ) : null}

      <Card
        title="Compensation metrics"
        description="Aggregated figures for the current reporting periods."
        padding="none"
        actions={
          <>
            <Badge tone="restricted">Sensitive</Badge>{' '}
            <Button
              size="sm"
              variant="secondary"
              onClick={insights.refresh}
              busy={insights.status === 'loading'}
            >
              Refresh
            </Button>
          </>
        }
      >
        <DataTable
          caption={`${DATASET_LABEL} for the People Analytics tenant`}
          columns={columns}
          rows={insights.rows}
          getRowKey={(row) => row.id}
          loading={insights.status === 'loading'}
          empty={
            <EmptyState
              title="No metrics returned"
              description="The backend returned no rows for this tenant and scope set."
            />
          }
        />
      </Card>

      <Text size="sm" tone="muted" style={{ marginTop: 'var(--ins-space-lg)' }}>
        Every row shown here was recorded in the platform audit log against your
        user. Salary columns are restricted at the warehouse role, not by this
        page.
      </Text>
    </>
  );
}
