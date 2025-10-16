import React from 'react';
import PropTypes from 'prop-types';
import './GuidancePanel.css';

const GuidancePanel = ({ schemaOverview, suggestedQueries }) => {
  const tables = schemaOverview?.tables || [];
  const suggestions = suggestedQueries || [];

  if (tables.length === 0 && suggestions.length === 0) {
    return null;
  }

  return (
    <div className="guidance-panel">
      {tables.length > 0 && (
        <div className="guidance-section">
          <h4>Key datasets I know</h4>
          <ul>
            {tables.slice(0, 5).map((table) => (
              <li key={table.name}>
                <strong>{table.name}</strong>
                {table.description && <span> — {table.description}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {suggestions.length > 0 && (
        <div className="guidance-section">
          <h4>Try asking</h4>
          <ul>
            {suggestions.slice(0, 5).map((suggestion, index) => (
              <li key={`${suggestion}-${index}`}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

GuidancePanel.propTypes = {
  schemaOverview: PropTypes.shape({
    tables: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        description: PropTypes.string,
      })
    ),
  }),
  suggestedQueries: PropTypes.arrayOf(PropTypes.string),
};

GuidancePanel.defaultProps = {
  schemaOverview: null,
  suggestedQueries: [],
};

export default GuidancePanel;
