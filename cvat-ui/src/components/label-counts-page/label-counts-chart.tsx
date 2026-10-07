// SPDX-License-Identifier: MIT

import React, { useMemo } from 'react';
import {
    Chart as ChartJS, BarElement, CategoryScale, LinearScale, Tooltip,
} from 'chart.js';
import type { ChartOptions } from 'chart.js';
import { Bar } from 'react-chartjs-2';

import type { LabelCount } from './label-counts-page';

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip);

const BAR_HEIGHT_PX = 22;
const AXIS_HEIGHT_PX = 40;
const FALLBACK_COLOR = '#1890ff';

// Horizontal bars: with COCO's 80 classes, names under vertical bars would be unreadable.
const OPTIONS: ChartOptions<'bar'> = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
        x: { beginAtZero: true, ticks: { precision: 0 } },
        y: { ticks: { autoSkip: false } },
    },
};

interface Props {
    labels: LabelCount[];
}

function LabelCountsChart({ labels }: Props): JSX.Element {
    const data = useMemo(() => ({
        labels: labels.map((label) => label.name),
        datasets: [{
            label: 'Annotations',
            data: labels.map((label) => label.count),
            backgroundColor: labels.map((label) => label.color || FALLBACK_COLOR),
        }],
    }), [labels]);

    return (
        <div className='cvat-label-counts-chart' style={{ height: labels.length * BAR_HEIGHT_PX + AXIS_HEIGHT_PX }}>
            <Bar data={data} options={OPTIONS} />
        </div>
    );
}

export default React.memo(LabelCountsChart);
