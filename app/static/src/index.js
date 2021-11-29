import React from 'react';
import ReactDOM from 'react-dom';
import { Route, Link, BrowserRouter as Router } from 'react-router-dom'
import App from './App';
//import 'bootstrap/dist/css/bootstrap.css';

const routing = (
  <React.StrictMode>
    <Router>
      <div>
        <Route path="/login/" component={App} />
        <Route path="/web3connectview/web3/:resource" component={App} />
        <Route path="/reactrenderview/:resource" component={Fab} />
      </div>
    </Router>
  </React.StrictMode>
)

ReactDOM.render(routing, document.getElementById('root'));
