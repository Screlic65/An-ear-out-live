import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
// We can leave App.css here, as it contains our main layout styles
import './App.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)