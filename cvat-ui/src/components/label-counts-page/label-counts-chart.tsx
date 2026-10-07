// SPDX-License-Identifier: MIT

import React, { useMemo } from 'react';
import {
    Chart as ChartJS, BarElement, CategoryScale, Legend, LinearScale, Tooltip,
} from 'chart.js';
import type { ChartData, ChartOptions } from 'chart.js';
import { Bar } from 'react-chartjs-2';

import type { LabelCount } from './label-counts-page';

ChartJS.register(BarElement, CategoryScale, Legend, LinearScale, Tooltip);

const BAR_HEIGHT_PX = 22;
const AXIS_HEIGHT_PX = 40;
const LEGEND_HEIGHT_PX = 32;
const FALLBACK_COLOR = '#8c8c8c';

const TYPE_COLORS: Record<string, string> = {
    rectangle: '#1677ff',
    polygon: '#52c41a',
    mask: '#faad14',
    polyline: '#13c2c2',
    points: '#eb2f96',
    ellipse: '#fa541c',
    cuboid: '#2f54eb',
    skeleton: '#a0d911',
    track: '#722ed1',
    tag: '#595959',
};

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

const STACKED_OPTIONS: ChartOptions<'bar'> = {
    ...OPTIONS,
    plugins: { legend: { display: true, position: 'top' } },
    scales: {
        x: { ...OPTIONS.scales?.x, stacked: true },
        y: { ...OPTIONS.scales?.y, stacked: true },
    },
};

interface Props {
    labels: LabelCount[];
    splitByType: boolean;
}

function buildData(labels: LabelCount[], splitByType: boolean): ChartData<'bar'> {
    const names = labels.map((label) => label.name);
    if (!splitByType) {
        return {
            labels: names,
            datasets: [{
                label: 'Annotations',
                data: labels.map((label) => label.count),
                backgroundColor: labels.map((label) => label.color || FALLBACK_COLOR),
            }],
        };
    }

    const types = [...new Set(labels.flatMap((label) => Object.keys(label.by_type)))].sort();
    return {
        labels: names,
        datasets: types.map((type) => ({
            label: type,
            data: labels.map((label) => label.by_type[type] ?? 0),
            backgroundColor: TYPE_COLORS[type] ?? FALLBACK_COLOR,
        })),
    };
}

function LabelCountsChart({ labels, splitByType }: Props): JSX.Element {
    const data = useMemo(() => buildData(labels, splitByType), [labels, splitByType]);
    const height = labels.length * BAR_HEIGHT_PX + AXIS_HEIGHT_PX + (splitByType ? LEGEND_HEIGHT_PX : 0);

    return (
        <div className='cvat-label-counts-chart' style={{ height }}>
            <Bar data={data} options={splitByType ? STACKED_OPTIONS : OPTIONS} />
        </div>
    );
}

export default React.memo(LabelCountsChart);
