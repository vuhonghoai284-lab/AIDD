import React from 'react';
import { DatePicker, Select, Space } from 'antd';
import { CalendarOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

export interface TimeRangeType {
  type: '7days' | '30days' | '6months' | 'this_year' | '1year' | 'custom';
  start_date?: string;
  end_date?: string;
}

interface OperationsTimeRangeSelectorProps {
  value?: TimeRangeType;
  onChange?: (timeRange: TimeRangeType) => void;
  loading?: boolean;
  style?: React.CSSProperties;
}

const TIME_RANGE_OPTIONS = [
  { value: '7days', label: '近7天' },
  { value: '30days', label: '近30天' },
  { value: '6months', label: '近半年' },
  { value: 'this_year', label: '今年' },
  { value: '1year', label: '近1年' },
  { value: 'custom', label: '自定义' },
];

const OperationsTimeRangeSelector: React.FC<OperationsTimeRangeSelectorProps> = ({
  value = { type: '30days' },
  onChange,
  loading = false,
  style,
}) => {
  const handleTimeRangeTypeChange = (type: string) => {
    const newTimeRange: TimeRangeType = { type: type as any };
    
    // 清除自定义日期范围
    if (type !== 'custom') {
      delete newTimeRange.start_date;
      delete newTimeRange.end_date;
    }
    
    onChange?.(newTimeRange);
  };

  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (!dates || !dates[0] || !dates[1]) {
      onChange?.({ type: 'custom' });
      return;
    }

    const newTimeRange: TimeRangeType = {
      type: 'custom',
      start_date: dates[0].format('YYYY-MM-DD'),
      end_date: dates[1].format('YYYY-MM-DD'),
    };

    onChange?.(newTimeRange);
  };

  const getDateRangeValue = (): [Dayjs, Dayjs] | undefined => {
    if (value.type === 'custom' && value.start_date && value.end_date) {
      return [dayjs(value.start_date), dayjs(value.end_date)];
    }
    return undefined;
  };

  const getDisabledDate = (current: Dayjs): boolean => {
    // 不能选择未来的日期
    return current && current > dayjs().endOf('day');
  };

  return (
    <div style={style}>
      <Space size="middle" wrap>
        <Space>
          <CalendarOutlined />
          <span>时间范围:</span>
        </Space>
        
        <Select
          value={value.type}
          onChange={handleTimeRangeTypeChange}
          loading={loading}
          style={{ minWidth: 120 }}
          size="middle"
        >
          {TIME_RANGE_OPTIONS.map(option => (
            <Option key={option.value} value={option.value}>
              {option.label}
            </Option>
          ))}
        </Select>

        {value.type === 'custom' && (
          <RangePicker
            value={getDateRangeValue()}
            onChange={handleDateRangeChange}
            disabledDate={getDisabledDate}
            format="YYYY-MM-DD"
            placeholder={['开始日期', '结束日期']}
            allowClear={false}
            size="middle"
          />
        )}
      </Space>
    </div>
  );
};

export default OperationsTimeRangeSelector;