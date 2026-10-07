// SPDX-License-Identifier: MIT

import './styles.scss';

import React, {
    useCallback, useEffect, useRef, useState,
} from 'react';
import { useParams } from 'react-router';
import { useSelector } from 'react-redux';
import { Row, Col } from 'antd/lib/grid';
import Title from 'antd/lib/typography/Title';
import Text from 'antd/lib/typography/Text';
import Result from 'antd/lib/result';
import Empty from 'antd/lib/empty';
import Button from 'antd/lib/button';
import Switch from 'antd/lib/switch';
import Tag from 'antd/lib/tag';

import { getCore } from 'cvat-core-wrapper';
import { CombinedState } from 'reducers';
import GoBackButton from 'components/common/go-back-button';
import CVATLoadingSpinner from 'components/common/loading-spinner';
import LabelCountsChart from './label-counts-chart';
import useLiveLabelCounts, { LiveStatus } from './use-live-label-counts';

const core = getCore();

export interface LabelCount {
    id: number;
    name: string;
    color: string;
    count: number;
    by_type: Record<string, number>;
}

interface LabelCounts {
    task_id: number;
    total: number;
    labels: LabelCount[];
}

type PageState =
    | { status: 'loading' }
    | { status: 'error'; message: string }
    | { status: 'ready'; counts: LabelCounts };

const LIVE_STATUS_TAGS: Record<LiveStatus, { color: string; text: string }> = {
    connecting: { color: 'default', text: 'Connecting' },
    live: { color: 'success', text: 'Live' },
    reconnecting: { color: 'warning', text: 'Reconnecting' },
    stopped: { color: 'default', text: 'Live updates off' },
};

async function fetchLabelCounts(taskId: number): Promise<LabelCounts> {
    const response = await core.server.request<{ data: LabelCounts }>(
        `${core.config.backendAPI}/test/tasks/${taskId}/label-counts`,
        { method: 'GET' },
    );
    return response.data;
}

function LabelCountsPage(): JSX.Element {
    const taskId = +useParams<{ tid: string }>().tid;
    const [state, setState] = useState<PageState>({ status: 'loading' });
    const [splitByType, setSplitByType] = useState(false);
    // Only the newest request may update the page, so a slow response can't overwrite a newer one.
    const latestRequest = useRef(0);

    const load = useCallback(async (): Promise<void> => {
        const requestId = ++latestRequest.current;
        setState({ status: 'loading' });
        try {
            const counts = await fetchLabelCounts(taskId);
            if (requestId === latestRequest.current) {
                setState({ status: 'ready', counts });
            }
        } catch (error: unknown) {
            if (requestId === latestRequest.current) {
                setState({ status: 'error', message: error instanceof Error ? error.message : String(error) });
            }
        }
    }, [taskId]);

    useEffect(() => {
        load();
        return () => {
            latestRequest.current += 1;
        };
    }, [load]);

    const organizationSlug = useSelector(
        (combinedState: CombinedState) => combinedState.organizations.current?.slug ?? '',
    );
    const onSnapshot = useCallback((counts: LabelCounts): void => {
        // A pushed snapshot is newer than any REST response still in flight.
        latestRequest.current += 1;
        setState({ status: 'ready', counts });
    }, []);
    const liveStatus = useLiveLabelCounts(taskId, organizationSlug, onSnapshot);
    const liveTag = LIVE_STATUS_TAGS[liveStatus];

    let content: JSX.Element;
    if (state.status === 'loading') {
        content = <CVATLoadingSpinner />;
    } else if (state.status === 'error') {
        content = (
            <Result
                status='error'
                title='Could not load annotation counts'
                subTitle={state.message}
                extra={<Button type='primary' onClick={load}>Retry</Button>}
            />
        );
    } else if (state.counts.total === 0) {
        content = (
            <Empty
                className='cvat-label-counts-empty'
                description={state.counts.labels.length ? 'No annotations in this task yet' : 'This task has no labels'}
            />
        );
    } else {
        const { total, labels } = state.counts;
        content = (
            <>
                <Row justify='space-between' align='middle'>
                    <Text type='secondary'>
                        {`${total} annotations across ${labels.length} labels`}
                    </Text>
                    <Text>
                        <Switch size='small' checked={splitByType} onChange={setSplitByType} />
                        {' Split by shape type'}
                    </Text>
                </Row>
                <LabelCountsChart labels={labels} splitByType={splitByType} />
            </>
        );
    }

    return (
        <div className='cvat-label-counts-page'>
            <Row justify='center'>
                <Col span={22} xl={18} xxl={14}>
                    <GoBackButton />
                    <Title level={4} className='cvat-text-color'>
                        {`Annotations per label, task #${taskId} `}
                        <Tag color={liveTag.color} className='cvat-label-counts-live-status'>{liveTag.text}</Tag>
                    </Title>
                    {content}
                </Col>
            </Row>
        </div>
    );
}

export default React.memo(LabelCountsPage);
