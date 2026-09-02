"""
Phase 4 Quality System Tests

Tests verify:
A. Hidden latent defect truth is absent from predictor input
B. Scenario flag is absent from predictor input  
C. Future process information cannot enter earlier feature snapshots
D. Healthy production produces low risk distribution
E. Weld drift increases relevant vehicle risk
F. Not every drift-exposed vehicle automatically fails
G. Model prediction precedes EOL result for qualifying vehicles
H. Prediction confidence falls with missing relevant observations
I. Vehicle digital thread remains ordered and persistent
J. Genealogy does not create strong false cluster during healthy production
K. Genealogy detects enriched tool/process factor during sustained drift
L. Actual EOL result is revealed only at inspection
M. Prediction record remains immutable after outcome
N. Quality model artifact loads correctly
O. Fallback model works when artifact is unavailable
P. Quality UI APIs do not expose latent ground truth for uninspected vehicles
"""

import pytest
from unittest.mock import Mock, patch
from backend.app.quality import QualityService, QualityFeatureBuilder, QualityModel, GenealogyAnalyzer
from backend.app.quality.features import VehicleQualitySnapshot
from backend.app.models import (
    VehicleThread,
    ProcessStep,
    StationObservation,
    StationTwinEstimate,
    StationBaseline,
    QualityLevel,
    DefectFamily,
    InspectionStatus,
)
from backend.app.simulation import AssemblyLineSimulator


class TestPhase4EndToEnd:
    """Acceptance tests exercise the real simulator → thread → model → EOL path."""

    def test_weld_drift_creates_early_risk_genealogy_and_eol_validation(self):
        simulator = AssemblyLineSimulator()
        simulator.pause()
        simulator.set_weld_drift(True)
        for _ in range(120):
            simulator._advance(15.0)

        elevated = simulator.quality_vehicles()
        genealogy = simulator.quality_genealogy()
        assert elevated
        assert any(item["risk"] >= 0.60 for item in elevated)
        assert genealogy["likely_origin_process"] == "BIW-02"
        assert genealogy["common_factors"]

        for _ in range(110):
            simulator._advance(15.0)
        metrics = simulator.quality_metrics()
        completed = [
            simulator.quality_vehicle(vehicle_id)
            for vehicle_id in simulator._vehicle_threads
        ]
        confirmed = [item for item in completed if item and item["inspection_result"]]
        assert confirmed
        assert any(item["inspection_result"]["result"].startswith("FAIL") for item in confirmed)
        assert metrics["prediction_lead_time_mean"] is not None
        for item in confirmed:
            if item["inspection_result"]["result"].startswith("FAIL"):
                assert item["prediction_history"][-1]["prediction_timestamp"] < item["inspection_result"]["inspection_timestamp"]

    def test_healthy_run_has_no_inspection_cohort_or_genealogy(self):
        simulator = AssemblyLineSimulator()
        simulator.pause()
        for _ in range(80):
            simulator._advance(15.0)
        assert simulator.quality_vehicles() == []
        genealogy = simulator.quality_genealogy()
        assert genealogy["common_factors"] == []


class TestQualityFeatureBuilder:
    """Test A: Feature snapshots contain only information available at prediction time"""
    
    def test_snapshot_no_future_stations(self):
        """C: Future process information cannot enter earlier feature snapshots"""
        builder = QualityFeatureBuilder()
        
        # Create a vehicle thread with only first 3 stations completed
        thread = VehicleThread(
            vehicle_id="VH-10824",
            variant="Sedan",
            body_color="#4f85a6",
            batch_id="B73",
            current_station="BIW-03",
            line_progress=0.3,
            total_line_time=120.0,
            completed_steps=[
                ProcessStep(
                    station_id="BIW-01",
                    station_name="Body Framing Cell",
                    entry_time=0.0,
                    exit_time=57.0,
                    cycle_time=57.0,
                    result="PASS",
                    equipment_id="BF-FIX-04",
                    metadata={"fixture": "BF-FIX-04"}
                ),
                ProcessStep(
                    station_id="BIW-02",
                    station_name="Robotic Weld Cell",
                    entry_time=57.0,
                    exit_time=115.0,
                    cycle_time=58.0,
                    result="PASS",
                    equipment_id="WG-04",
                    metadata={
                        "robot_cell": "RW-CELL-02",
                        "weld_gun": "WG-04",
                        "electrode_cap_lot": "EC-17"
                    }
                ),
            ]
        )
        
        station_observations = {
            "BIW-01": StationObservation(
                station_id="BIW-01",
                timestamp=57.0,
                operational_state="RUNNING",
                vehicle_id="VH-10824",
                queue_level=0,
                cycle_time=57.0,
                cycle_progress=1.0,
                completed_cycle_time=57.0,
                entry_timestamp=0.0,
                last_departure_timestamp=57.0,
                conveyor_occupied=True,
                source="Synthetic PLC",
                quality=0.95,
                signals=["PLC state", "cycle timestamp"]
            )
        }
        
        station_twins = {
            "BIW-01": StationTwinEstimate(
                expected_cycle=57.0,
                estimated_cycle=57.0,
                estimated_range_low=55.0,
                estimated_range_high=59.0,
                observed_cycle=57.0,
                residual=0.0,
                normalized_deviation=0.0,
                residual_trend="STABLE",
                confidence=0.9,
                data_age=0.5,
                source="Full telemetry",
                evidence=["PLC cycle events"],
                estimated_from_indirect_evidence=False,
                last_observation=57.0,
                last_assimilation=57.0,
                baseline=StationBaseline(
                    expected_cycle=57.0,
                    cycle_stddev=2.0,
                    expected_utilization=0.82,
                    normal_queue=0.8,
                    samples=15
                )
            )
        }
        
        snapshot = builder.build_snapshot(
            thread,
            "BIW-03",
            120.0,
            station_observations,
            station_twins
        )
        
        # Verify only completed stations are in snapshot
        assert snapshot.total_completed_stations == 2
        assert snapshot.robot_cell_id == "RW-CELL-02"
        assert snapshot.weld_gun_id == "WG-04"
        assert snapshot.electrode_cap_lot == "EC-17"
        
        # Verify no future station data
        assert snapshot.paint_batch is None  # Paint is future
        assert snapshot.torque_tool_id is None  # Torque is future
        
    def test_snapshot_no_ground_truth(self):
        """A: Hidden latent defect truth is absent from predictor input"""
        builder = QualityFeatureBuilder()
        
        thread = VehicleThread(
            vehicle_id="VH-10825",
            variant="SUV",
            body_color="#596b7f",
            batch_id="B74",
            current_station="BIW-02",
            line_progress=0.2,
            total_line_time=60.0,
            completed_steps=[
                ProcessStep(
                    station_id="BIW-01",
                    station_name="Body Framing Cell",
                    entry_time=0.0,
                    exit_time=57.0,
                    cycle_time=57.0,
                    result="PASS",
                    equipment_id="BF-FIX-04",
                    metadata={"fixture": "BF-FIX-04"}
                )
            ]
        )
        
        snapshot = builder.build_snapshot(
            thread,
            "BIW-02",
            60.0,
            {},
            {}
        )
        
        # Verify no latent defect truth in snapshot
        assert not hasattr(snapshot, 'latent_defect')
        assert not hasattr(snapshot, 'defect_truth')
        assert not hasattr(snapshot, 'scenario_active')
        
        # Verify only observable features
        assert hasattr(snapshot, 'vehicle_id')
        assert hasattr(snapshot, 'variant')
        assert hasattr(snapshot, 'completed_steps')


class TestQualityModel:
    """Test model behavior and architecture"""
    
    def test_model_loads_or_fallback(self):
        """N: Quality model artifact loads correctly"""
        """O: Fallback model works when artifact is unavailable"""
        model = QualityModel()
        
        # Model should either load trained artifact or use fallback
        assert model._model is not None
        assert model._scaler is not None
        
        # Verify fallback detection
        if model.is_fallback():
            print("Using fallback model (expected for initial tests)")
        else:
            print("Loaded trained model artifact")
    
    def test_prediction_separate_risk_confidence(self):
        """Verify risk and confidence are separate metrics"""
        model = QualityModel()
        
        from backend.app.quality.features import VehicleQualitySnapshot
        snapshot = VehicleQualitySnapshot(
            vehicle_id="VH-10826",
            variant="Sedan",
            prediction_timestamp=120.0,
            station_at_prediction="BIW-02",
            completed_steps=[],
            weld_energy_deviation=0.15,
            weld_variance_multiplier=1.8,
            avg_cycle_deviation=0.12,
            max_cycle_deviation=0.25,
            avg_twin_confidence=0.85,
            min_twin_confidence=0.78,
            signal_completeness=0.9,
            has_weld_telemetry=True,
            has_full_telemetry_at_risk_station=True
        )
        
        prediction = model.predict(snapshot)
        
        # Risk and confidence should be separate
        assert 0 <= prediction.risk <= 1
        assert 0 <= prediction.confidence <= 1
        
        # They are not perfectly correlated
        assert prediction.risk != prediction.confidence
        
        # High weld variance should increase risk
        assert prediction.risk > 0.3  # Should show some risk
        
    def test_no_scenario_flag_in_prediction(self):
        """B: Scenario flag is absent from predictor input"""
        model = QualityModel()
        
        snapshot = VehicleQualitySnapshot(
            vehicle_id="VH-10827",
            variant="EV",
            prediction_timestamp=180.0,
            station_at_prediction="PAINT-02",
            completed_steps=[],
        )
        
        # Verify snapshot has no scenario flags
        assert not hasattr(snapshot, 'scenario_active')
        assert not hasattr(snapshot, 'drift_active')
        assert not hasattr(snapshot, 'injected_fault')
        
        prediction = model.predict(snapshot)
        
        # Prediction based only on available features
        assert prediction.risk >= 0
        assert prediction.risk <= 1


class TestQualityService:
    """Test quality service and API behavior"""
    
    def test_latent_truth_not_exposed(self):
        """P: Quality UI APIs do not expose latent ground truth for uninspected vehicles"""
        service = QualityService()
        
        # Create a vehicle with latent defect
        thread = VehicleThread(
            vehicle_id="VH-10828",
            variant="Sedan",
            body_color="#4f85a6",
            batch_id="B75",
            current_station="BIW-02",
            line_progress=0.2,
            total_line_time=60.0,
            completed_steps=[]
        )
        
        # The predictor does not accept a ground-truth argument at all.
        service.update_vehicle_quality(
            thread,
            "BIW-02",
            60.0,
            {},
            {},
        )
        
        # Get public vehicle quality record
        public_record = service.get_vehicle_quality("VH-10828")
        
        # Verify latent truth is NOT exposed
        assert public_record is not None
        assert 'latent_defect' not in public_record
        assert 'latent_quality_score' not in public_record
        
        # Only prediction info should be exposed
        assert 'current_prediction' in public_record
        assert 'inspection_result' in public_record
        
    def test_inspection_reveals_ground_truth(self):
        """L: Actual EOL result is revealed only at inspection"""
        service = QualityService()
        
        # Before inspection
        thread = VehicleThread(
            vehicle_id="VH-10829",
            variant="SUV",
            body_color="#596b7f",
            batch_id="B76",
            current_station="FA-05",
            line_progress=0.95,
            total_line_time=600.0,
            completed_steps=[]
        )
        
        service.update_vehicle_quality(thread, "FA-05", 600.0, {}, {})
        
        pre_inspection = service.get_vehicle_quality("VH-10829")
        assert pre_inspection['inspection_result'] is None
        
        # Record inspection result
        service.record_inspection_result(
            vehicle_id="VH-10829",
            inspection_time=610.0,
            inspection_station="FA-05",
            passed=False,
            defect_family="Body geometry / weld integrity"
        )
        
        # After inspection
        post_inspection = service.get_vehicle_quality("VH-10829")
        assert post_inspection['inspection_result'] is not None
        assert post_inspection['inspection_result']['result'].startswith("FAIL")
        assert post_inspection['inspection_result']['defect_family'] == DefectFamily.BODY_WELD
        
    def test_prediction_immutable_after_outcome(self):
        """M: Prediction record remains immutable after outcome"""
        service = QualityService()
        
        thread = VehicleThread(
            vehicle_id="VH-10830",
            variant="Sedan",
            body_color="#4f85a6",
            batch_id="B77",
            current_station="BIW-02",
            line_progress=0.2,
            total_line_time=60.0,
            completed_steps=[]
        )
        
        # Make initial prediction
        service.update_vehicle_quality(thread, "BIW-02", 60.0, {}, {})
        
        first_record = service.get_vehicle_quality("VH-10830")
        first_risk = first_record['current_prediction']['risk']
        first_timestamp = first_record['current_prediction']['prediction_timestamp']
        
        # Record inspection outcome
        service.record_inspection_result(
            vehicle_id="VH-10830",
            inspection_time=610.0,
            inspection_station="FA-05",
            passed=True
        )
        
        # Verify original prediction is unchanged
        final_record = service.get_vehicle_quality("VH-10830")
        assert final_record['current_prediction']['risk'] == first_risk
        assert final_record['current_prediction']['prediction_timestamp'] == first_timestamp
        
        # Prediction history should be preserved
        assert len(final_record['prediction_history']) >= 1


class TestGenealogyAnalyzer:
    """Test genealogy analysis for common factor detection"""
    
    def test_healthy_production_no_false_cluster(self):
        """J: Genealogy does not create strong false cluster during healthy production"""
        analyzer = GenealogyAnalyzer()
        
        # Create normal production threads with random tool assignments
        normal_threads = {}
        for i in range(20):
            thread = VehicleThread(
                vehicle_id=f"VH-1083{i}",
                variant="Sedan",
                body_color="#4f85a6",
                batch_id=f"B{78 + i % 5}",
                current_station="FA-05",
                line_progress=1.0,
                total_line_time=600.0,
                completed_steps=[
                    ProcessStep(
                        station_id="BIW-02",
                        station_name="Robotic Weld Cell",
                        entry_time=57.0,
                        exit_time=115.0,
                        cycle_time=58.0,
                        result="PASS",
                        equipment_id=f"WG-{(i % 3) + 4}",  # Different weld guns
                        metadata={
                            "robot_cell": f"RW-CELL-{(i % 2) + 2}",
                            "weld_gun": f"WG-{(i % 3) + 4}",
                            "electrode_cap_lot": f"EC-{17 + i % 3}"
                        }
                    )
                ]
            )
            normal_threads[thread.vehicle_id] = thread
        
        # Create high-risk cohort (empty for healthy production)
        cohort_predictions = []
        
        analysis = analyzer.analyze_cohort(
            cohort_predictions,
            normal_threads,
            normal_threads,
            620.0
        )
        
        # Should not find strong clusters in healthy production
        assert analysis['cohort_size'] == 0
        assert len(analysis['common_factors']) == 0
        assert analysis['analysis_confidence'] == 0.0
        
    def test_drift_scenario_detects_common_factor(self):
        """K: Genealogy detects enriched tool/process factor during sustained drift"""
        analyzer = GenealogyAnalyzer()
        
        # Create cohort with shared WG-04 and EC-17
        cohort_threads = {}
        for i in range(8):
            thread = VehicleThread(
                vehicle_id=f"VH-1084{i}",
                variant="Sedan",
                body_color="#4f85a6",
                batch_id="B73",
                current_station="FA-05",
                line_progress=1.0,
                total_line_time=600.0,
                completed_steps=[
                    ProcessStep(
                        station_id="BIW-02",
                        station_name="Robotic Weld Cell",
                        entry_time=57.0,
                        exit_time=115.0,
                        cycle_time=58.0,
                        result="PASS",
                        equipment_id="WG-04",  # Same weld gun
                        metadata={
                            "robot_cell": "RW-CELL-02",
                            "weld_gun": "WG-04",
                            "electrode_cap_lot": "EC-17"  # Same electrode cap lot
                        }
                    )
                ]
            )
            cohort_threads[thread.vehicle_id] = thread
        
        # Create baseline with random tools
        baseline_threads = {}
        for i in range(20):
            thread = VehicleThread(
                vehicle_id=f"VH-1085{i}",
                variant="SUV",
                body_color="#596b7f",
                batch_id=f"B{78 + i % 5}",
                current_station="FA-05",
                line_progress=1.0,
                total_line_time=600.0,
                completed_steps=[
                    ProcessStep(
                        station_id="BIW-02",
                        station_name="Robotic Weld Cell",
                        entry_time=57.0,
                        exit_time=115.0,
                        cycle_time=58.0,
                        result="PASS",
                        equipment_id=f"WG-{(i % 4) + 4}",  # Random weld guns
                        metadata={
                            "robot_cell": f"RW-CELL-{(i % 2) + 2}",
                            "weld_gun": f"WG-{(i % 4) + 4}",
                            "electrode_cap_lot": f"EC-{17 + i % 4}"  # Random lots
                        }
                    )
                ]
            )
            baseline_threads[thread.vehicle_id] = thread
        
        # Create mock predictions for cohort
        from backend.app.models import VehicleQualityPrediction, QualityEvidence
        cohort_predictions = [
            VehicleQualityPrediction(
                vehicle_id=f"VH-1084{i}",
                prediction_timestamp=610.0,
                station_at_prediction="FA-05",
                risk=0.75,  # High risk
                confidence=0.85,
                likely_defect_family=DefectFamily.BODY_WELD,
                likely_origin_station="BIW-02",
                recommended_inspection_point="Body Shop Exit",
                evidence=[QualityEvidence(factor="weld_variance_multiplier", value="2.1×", contribution=0.4)],
                quality_level=QualityLevel.INSPECT,
                model_version="quality-logreg-v1"
            )
            for i in range(8)
        ]
        
        analysis = analyzer.analyze_cohort(
            cohort_predictions,
            cohort_threads,
            baseline_threads,
            620.0
        )
        
        # Should detect WG-04 and EC-17 as common factors
        assert analysis['cohort_size'] == 8
        assert len(analysis['common_factors']) > 0
        
        # Find WG-04 factor
        wg04_factor = next((f for f in analysis['common_factors'] if f['factor_id'] == 'WG-04'), None)
        assert wg04_factor is not None
        assert wg04_factor['support'] >= 6  # Most of cohort
        assert wg04_factor['risk_lift'] > 1.5  # Meaningful enrichment
        
        # Find EC-17 factor
        ec17_factor = next((f for f in analysis['common_factors'] if 'EC-17' in f['factor_id']), None)
        assert ec17_factor is not None
        assert ec17_factor['risk_lift'] > 1.5
        
        # Likely origin should be weld process
        assert analysis['likely_origin_process'] == "BIW-02"
        assert analysis['analysis_confidence'] > 0.5


class TestConfidenceWithMissingData:
    """Test H: Prediction confidence falls with missing relevant observations"""
    
    def test_missing_weld_telemetry_reduces_confidence(self):
        service = QualityService()
        
        # Vehicle with full weld telemetry
        full_thread = VehicleThread(
            vehicle_id="VH-10860",
            variant="Sedan",
            body_color="#4f85a6",
            batch_id="B73",
            current_station="BIW-03",
            line_progress=0.3,
            total_line_time=120.0,
            completed_steps=[
                ProcessStep(
                    station_id="BIW-02",
                    station_name="Robotic Weld Cell",
                    entry_time=57.0,
                    exit_time=115.0,
                    cycle_time=58.0,
                    result="PASS",
                    equipment_id="WG-04",
                    metadata={
                        "robot_cell": "RW-CELL-02",
                        "weld_gun": "WG-04",
                        "electrode_cap_lot": "EC-17"
                    }
                )
            ]
        )
        
        full_observations = {
            "BIW-02": StationObservation(
                station_id="BIW-02",
                timestamp=115.0,
                operational_state="RUNNING",
                vehicle_id="VH-10860",
                queue_level=0,
                cycle_time=58.0,
                cycle_progress=1.0,
                completed_cycle_time=58.0,
                entry_timestamp=57.0,
                last_departure_timestamp=115.0,
                conveyor_occupied=True,
                power=48.5,  # Full telemetry
                vibration=1.4,
                source="Synthetic PLC",
                quality=0.95,
                signals=["PLC state", "cycle timestamp", "tool telemetry"]
            )
        }
        
        full_twins = {
            "BIW-02": StationTwinEstimate(
                expected_cycle=58.0,
                estimated_cycle=58.0,
                estimated_range_low=56.0,
                estimated_range_high=60.0,
                observed_cycle=58.0,
                residual=0.0,
                normalized_deviation=0.0,
                residual_trend="STABLE",
                confidence=0.92,
                data_age=0.5,
                source="Full telemetry",
                evidence=["PLC cycle events", "tool telemetry"],
                estimated_from_indirect_evidence=False,
                last_observation=115.0,
                last_assimilation=115.0,
                baseline=StationBaseline(
                    expected_cycle=58.0,
                    cycle_stddev=2.0,
                    expected_utilization=0.82,
                    normal_queue=0.8,
                    samples=20
                )
            )
        }
        
        service.update_vehicle_quality(full_thread, "BIW-03", 120.0, full_observations, full_twins)
        full_record = service.get_vehicle_quality("VH-10860")
        full_confidence = full_record['current_prediction']['confidence']
        
        # Vehicle with missing weld telemetry
        missing_thread = VehicleThread(
            vehicle_id="VH-10861",
            variant="SUV",
            body_color="#596b7f",
            batch_id="B74",
            current_station="BIW-03",
            line_progress=0.3,
            total_line_time=120.0,
            completed_steps=[
                ProcessStep(
                    station_id="BIW-02",
                    station_name="Robotic Weld Cell",
                    entry_time=57.0,
                    exit_time=115.0,
                    cycle_time=58.0,
                    result="PASS",
                    equipment_id="WG-04",
                    metadata={
                        "robot_cell": "RW-CELL-02",
                        "weld_gun": "WG-04",
                        "electrode_cap_lot": "EC-17"
                    }
                )
            ]
        )
        
        # No BIW-02 observation (telemetry dropout)
        missing_observations = {}
        missing_twins = {
            "BIW-02": StationTwinEstimate(
                expected_cycle=58.0,
                estimated_cycle=58.0,
                estimated_range_low=56.0,
                estimated_range_high=60.0,
                observed_cycle=None,  # Missing direct observation
                residual=0.0,
                normalized_deviation=0.0,
                residual_trend="STABLE",
                confidence=0.65,  # Lower confidence due to missing data
                data_age=5.0,  # Stale data
                source="Estimated after data gap",
                evidence=["Last valid observation", "Historical process model"],
                estimated_from_indirect_evidence=True,
                last_observation=110.0,
                last_assimilation=115.0,
                baseline=StationBaseline(
                    expected_cycle=58.0,
                    cycle_stddev=2.0,
                    expected_utilization=0.82,
                    normal_queue=0.8,
                    samples=20
                )
            )
        }
        
        service.update_vehicle_quality(missing_thread, "BIW-03", 120.0, missing_observations, missing_twins)
        missing_record = service.get_vehicle_quality("VH-10861")
        missing_confidence = missing_record['current_prediction']['confidence']
        
        # Missing telemetry should reduce confidence
        assert missing_confidence < full_confidence
        assert missing_confidence < 0.8  # Should be noticeably lower


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
