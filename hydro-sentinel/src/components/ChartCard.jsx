// Sistem Monitoring/hydro-sentinel/src/components/ChartCard.jsx

import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  Title,
  CategoryScale,
  Tooltip,
  Legend
} from "chart.js";
import annotationPlugin from 'chartjs-plugin-annotation';

import "../styles/css/Chart.css";

ChartJS.register(
  LineElement,
  PointElement,
  LinearScale,
  Title,
  CategoryScale,
  Tooltip,
  Legend,
  annotationPlugin
);

export default function ChartCard({ parameter, data }) {
  const parameterConfig = {
    "pH Level": {
      key: "ph",
      threshold: { min: 6.5, max: 8.5 },
      color: "#ca01e2",
      class: "ph"
    },
    "Temperature": {
      key: "temperature",
      threshold: { min: 27, max: 33 },
      color: "#ff9601",
      class: "temperature"
    },
    "TDS": {
      key: "tds",
      threshold: { min: 0, max: 300 },
      color: "#818181",
      class: "tds"
    },
    "Turbidity": {
      key: "turbidity",
      threshold: { min: 0, max: 3 },
      color: "#c87400",
      class: "turbidity"
    },
  };

  const selectedConfig = parameterConfig[parameter] || {
    key: null,
    threshold: null,
    color: null
  };

  const parameterKey = selectedConfig.key;
  const parameterThreshold = selectedConfig.threshold;
  const parameterColor = selectedConfig.color;
  const parameterClass = selectedConfig.class;

  // const labels = data.map((item) =>
  //   new Date(Number(item.timestamp)).toLocaleTimeString("id-ID", {
  //     hour: "2-digit",
  //     minute: "2-digit",
  //     second: "2-digit",
  //   })
  // );

  const labels = data.map((item) => item.time);

  const values = data.map((item) => item[parameterKey]);

  const chartData = {
    labels,
    datasets: [
      {
        label: parameter,
        data: values,
        fill: false,
        borderColor: parameterColor,
        pointBackgroundColor: parameterColor,
        tension: 0,
        pointRadius: 1,
        pointHoverRadius: 5,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.parsed.y}`,
        },
      },
      annotation: parameterThreshold
      ? {
          annotations: {
            minLine: {
              type: "line",
              yMin: parameterThreshold.min,
              yMax: parameterThreshold.min,
              borderColor: "red",
              borderWidth: 1,
              borderDash: [6, 6],
              label: {
                content: "Min",
                enabled: true,
                position: "start",
                backgroundColor: "red",
              },
            },
            maxLine: {
              type: "line",
              yMin: parameterThreshold.max,
              yMax: parameterThreshold.max,
              borderColor: "red",
              borderWidth: 1,
              borderDash: [6, 6],
              label: {
                content: "Max",
                enabled: true,
                position: "start",
                backgroundColor: "red",
              },
            },
          },
        }
      : {},
    },
    scales: {
      y: {
        beginAtZero: false,
        suggestedMin: parameterThreshold ? parameterThreshold.min - (parameterThreshold.max - parameterThreshold.min) * 0.1 : undefined,
        suggestedMax: parameterThreshold ? parameterThreshold.max + (parameterThreshold.max - parameterThreshold.min) * 0.1 : undefined,
      },
    },
  };

  return (
    <div className={`ChartCard-container ${parameterClass}`}>
      <h3>{parameter}</h3>
      <Line data={chartData} options={options} />
    </div>
  );
}
