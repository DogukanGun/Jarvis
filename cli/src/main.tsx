import React from 'react'
import { render } from 'ink'
import App from './components/App.js'

// Clear the terminal before Ink takes over — prevents the pre-render
// shell output from bleeding through on every re-render cycle.
process.stdout.write('\x1b[2J\x1b[H')

render(<App />)
