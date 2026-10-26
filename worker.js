importScripts('./model.js');
self.onmessage = event => {
  try { self.postMessage({ id: event.data.id, result: ShiftLab.train(event.data.config) }); }
  catch (error) { self.postMessage({ id: event.data.id, error: error.message }); }
};
