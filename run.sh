#!/usr/bin/with-contenv bashio
# ==============================================================================
# GivTCP Home Assistant Add-on
# Starts GivTCP with configuration from Home Assistant
# ==============================================================================

bashio::log.info "Starting GivTCP..."

# Read configuration from Home Assistant add-on options
CONFIG_PATH=/data/options.json

# Required settings
export INVERTOR_IP=$(bashio::config 'invertor_ip')
export INVERTOR_NUM_BATTERIES=$(bashio::config 'num_batteries')

# MQTT settings
export MQTT_ADDRESS=$(bashio::config 'mqtt_address')
export MQTT_USERNAME=$(bashio::config 'mqtt_username' '')
export MQTT_PASSWORD=$(bashio::config 'mqtt_password' '')
export MQTT_TOPIC=$(bashio::config 'mqtt_topic')

# Home Assistant integration
export HA_AUTO_D=$(bashio::config 'ha_auto_discovery')

# Logging
export LOG_LEVEL=$(bashio::config 'log_level')
export PRINT_RAW=$(bashio::config 'print_raw' 'False')

# Application settings
export SELF_RUN_LOOP_TIMER=$(bashio::config 'self_run_loop_timer')
export QUEUE_RETRIES=$(bashio::config 'queue_retries' '2')
export CACHELOCATION="/config"

# Data smoothing
export DATASMOOTHER=$(bashio::config 'datasmoother' 'High')

# PALM settings (optional)
if bashio::config.exists 'palm_winter'; then
    export PALM_WINTER=$(bashio::config 'palm_winter')
fi

if bashio::config.exists 'palm_shoulder'; then
    export PALM_SHOULDER=$(bashio::config 'palm_shoulder')
fi

if bashio::config.exists 'palm_min_soc_target'; then
    export PALM_MIN_SOC_TARGET=$(bashio::config 'palm_min_soc_target')
fi

if bashio::config.exists 'palm_max_soc_target'; then
    export PALM_MAX_SOC_TARGET=$(bashio::config 'palm_max_soc_target')
fi

if bashio::config.exists 'palm_batt_reserve'; then
    export PALM_BATT_RESERVE=$(bashio::config 'palm_batt_reserve')
fi

if bashio::config.exists 'palm_batt_utilisation'; then
    export PALM_BATT_UTILISATION=$(bashio::config 'palm_batt_utilisation')
fi

# InfluxDB settings (optional)
if bashio::config.exists 'influx_output'; then
    export INFLUX_OUTPUT=$(bashio::config 'influx_output')

    if bashio::config.true 'influx_output'; then
        export INFLUX_URL=$(bashio::config 'influx_url')
        export INFLUX_TOKEN=$(bashio::config 'influx_token')
        export INFLUX_BUCKET=$(bashio::config 'influx_bucket')
        export INFLUX_ORG=$(bashio::config 'influx_org')
    fi
fi

# Phase 1-5 Refactoring Feature Flags
export USE_NEW_CACHE=$(bashio::config 'feature_flag_use_new_cache' 'false')
export USE_NEW_LOCKS=$(bashio::config 'feature_flag_use_new_locks' 'false')
export USE_NEW_SERVICES=$(bashio::config 'feature_flag_use_new_services' 'false')

# Log feature flag status
bashio::log.info "Feature Flags:"
bashio::log.info "  USE_NEW_CACHE=${USE_NEW_CACHE}"
bashio::log.info "  USE_NEW_LOCKS=${USE_NEW_LOCKS}"
bashio::log.info "  USE_NEW_SERVICES=${USE_NEW_SERVICES}"

# Validate required settings
if bashio::config.is_empty 'invertor_ip'; then
    bashio::log.fatal "Invertor IP address is required!"
    bashio::exit.nok "Please configure the invertor_ip in the add-on settings."
fi

bashio::log.info "Configuration loaded successfully"
bashio::log.info "Invertor IP: ${INVERTOR_IP}"
bashio::log.info "Number of batteries: ${INVERTOR_NUM_BATTERIES}"
bashio::log.info "MQTT address: ${MQTT_ADDRESS}"

# Start GivTCP
bashio::log.info "Starting GivTCP application..."
cd /app || bashio::exit.nok "Could not change to /app directory"

exec python3 /app/startup.py
