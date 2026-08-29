const { withInfoPlist } = require("expo/config-plugins");

module.exports = function withProcessingOnly(config) {
  return withInfoPlist(config, (result) => {
    const modes = new Set(result.modResults.UIBackgroundModes ?? []);
    modes.add("processing");
    modes.delete("remote-notification");
    result.modResults.UIBackgroundModes = [...modes];
    return result;
  });
};
