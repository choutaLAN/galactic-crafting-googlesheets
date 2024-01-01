function createTimeDrivenTrigger() {
  // Create a trigger for the function you want to run
  ScriptApp.newTrigger('manualUpdate')
    .timeBased()
    .everyMinutes(1)
    .create();
}
