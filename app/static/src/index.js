import React from 'react';
import ReactDOM from 'react-dom';
import { Route, Link, BrowserRouter as Router } from 'react-router-dom'
import App from './App';

const routing = (
  <React.StrictMode>
    <Router>
      <div>
        <Route path="/web3connectview/web3/:resource" component={App} />
      </div>
    </Router>
  </React.StrictMode>
)

ReactDOM.render(routing, document.getElementById('root'));
